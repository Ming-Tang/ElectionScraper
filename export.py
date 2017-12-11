import pickle
import ujson as json
import pandas as pd

with open("output/db.pickle", "rb") as f:
    db = pickle.load(f)

json_data = {
    kk: {str(k[0]): v.data for k, v in vv.items()}
    for kk, vv in db.data.items()
}

with open('output/data_full.json', 'w') as f:
    json.dump(json_data, f, indent=2, sort_keys=True)

for kk, vv in json_data.items():
   df = pd.DataFrame.from_dict(vv, orient='index')
   df.to_csv("output/{}.csv".format(kk), index=False, na_rep='NA')

