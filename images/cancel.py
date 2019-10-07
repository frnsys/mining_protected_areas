import ee
from tqdm import tqdm
from multiprocessing import Pool

ee.Initialize()
tasks = ee.data.getTaskList()

def cancel(t):
    if t['state'] in ['READY', 'RUNNING']:
        ee.data.cancelTask(t['id'])

with Pool() as p:
    for _ in tqdm(p.imap(cancel, tasks), total=len(tasks), desc='Cancelling tasks'):
        pass
# import ipdb; ipdb.set_trace()

