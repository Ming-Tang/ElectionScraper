import riding_scraper
import election_scraper
import schema
import pickle
import json
import logging

db = schema.make_standard_database()

db1 = riding_scraper.main()
db2 = election_scraper.main()

logging.info("Updating database...")
db.update_from(db1)
db.update_from(db2)

with open("output/db.pickle", "wb") as f:
    pickle.dump(db, file=f)

