"""
Backfill Parallel Extractions to Core Tables

Coalesces data from extracted.parallel_* tables into core.* tables.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class BackfillParallelRequest(BaseModel):
    """Request model for parallel backfill."""
    batch_size: Optional[int] = 5000
    backfill_customers: Optional[bool] = True
    backfill_champions: Optional[bool] = True


class BackfillParallelResponse(BaseModel):
    """Response model for parallel backfill."""
    success: bool
    customers_updated: Optional[int] = None
    champions_inserted: Optional[int] = None
    error: Optional[str] = None


DATABASE_URL = "postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=600,
)
@modal.fastapi_endpoint(method="POST")
def backfill_parallel_to_core(request: BackfillParallelRequest) -> BackfillParallelResponse:
    """
    Backfill data from parallel extractions to core tables.

    - Backfills customer_domain from extracted.parallel_case_studies to core.company_customers
    - Backfills champions from extracted.parallel_case_study_champions to core.case_study_champions
    """
    import psycopg2

    customers_updated = 0
    champions_inserted = 0

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Backfill customer domains
        if request.backfill_customers:
            cur.execute("""
                UPDATE core.company_customers cc
                SET
                    customer_domain = pcs.customer_company_domain,
                    customer_domain_source = 'parallel-case-studies-backfill',
                    updated_at = NOW()
                FROM extracted.parallel_case_studies pcs
                WHERE cc.case_study_url = pcs.case_study_url
                    AND cc.origin_company_domain = pcs.origin_company_domain
                    AND pcs.customer_company_domain IS NOT NULL
                    AND cc.customer_domain IS NULL
            """)
            customers_updated = cur.rowcount
            conn.commit()

        # Backfill champions in batches
        if request.backfill_champions:
            batch_size = request.batch_size or 5000
            offset = 0

            while True:
                cur.execute("""
                    INSERT INTO core.case_study_champions (
                        full_name,
                        job_title,
                        company_name,
                        company_domain,
                        origin_company_domain,
                        case_study_url,
                        source
                    )
                    SELECT
                        pcc.full_name,
                        pcc.job_title,
                        pcs.customer_company_name,
                        pcc.customer_company_domain,
                        pcc.origin_company_domain,
                        pcs.case_study_url,
                        'parallel-case-studies-backfill'
                    FROM extracted.parallel_case_study_champions pcc
                    JOIN extracted.parallel_case_studies pcs ON pcc.case_study_id = pcs.id
                    ORDER BY pcc.created_at
                    LIMIT %s OFFSET %s
                    ON CONFLICT (full_name, company_domain, case_study_url) DO NOTHING
                """, (batch_size, offset))

                batch_inserted = cur.rowcount
                champions_inserted += batch_inserted
                conn.commit()

                if batch_inserted == 0:
                    break

                offset += batch_size

        cur.close()
        conn.close()

        return BackfillParallelResponse(
            success=True,
            customers_updated=customers_updated,
            champions_inserted=champions_inserted
        )

    except Exception as e:
        import traceback
        return BackfillParallelResponse(
            success=False,
            error=f"{str(e)}\n{traceback.format_exc()}"
        )
