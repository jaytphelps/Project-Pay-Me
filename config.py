import os
ENV = os.getenv("ENV", "dev")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data/raw"))
LOG_DIR  = os.getenv("LOG_DIR", os.path.join(BASE_DIR, "logs"))
DB_DIR = os.getenv("DB_DIR", os.path.join(BASE_DIR, "db"))
REFERENCE_DIR = os.getenv("REFERENCE_DIR", os.path.join(BASE_DIR, "data/reference"))
DB_FILE = os.getenv("DB_FILE", os.path.join(DB_DIR, "FinancialPolDB.db"))
LDA_API_URL = "https://lda.senate.gov/api/v1/filings/"
LDA_API_KEY = os.getenv("LDA_API_KEY", "")
CONGRESS_BULK_URL = "https://www.govinfo.gov/bulkdata/BILLSTATUS"

# CONGRESS_API_KEY = os.getenv("LDA_API_KEY", "")
FEC_API_URL = "https://www.fec.gov/files/bulk-downloads"
FEC_API_KEY = os.getenv("FEC_API_KEY")

STOCK_ACT_HOUSE_INDEX = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs"
STOCK_ACT_PTR_BASE = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs"

PAGE_SIZE   = 25
MAX_RETRIES = 3
RETRY_WAIT  = 30
MAX_FILINGS = 1000
CHECKPOINT_EVERY = 50
RECORDS_PER_FILE = 100000
