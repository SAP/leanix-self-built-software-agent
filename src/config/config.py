import os


DEFAULT_IS_LOCAL = os.getenv("DEFAULT_IS_LOCAL", False)

########################################
# DB
########################################
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///sbs-ai-discovery.db")