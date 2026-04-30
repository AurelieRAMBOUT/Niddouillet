# Chemins

BASE_DIR = ROOT_DIR

ANNONCES_CSV = DATA_DIR / "annonces.csv"
DVF_CSV = DATA_DIR / "dvf_toulon.csv"

SCRIPT_DIR = ROOT_DIR / "scripts"
if not SCRIPT_DIR.exists():
    SCRIPT_DIR = BACKEND_DIR / "scripts"

SCRAPE_SCRIPT = SCRIPT_DIR / "run_scrape_multi_sites.py"

LOGO_PATH = FRONTEND_DIR / "logo_niddouillet.png"