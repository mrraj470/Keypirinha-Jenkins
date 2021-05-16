import os
import pickle
import shutil


class Cache:
    def __init__(self, cache_path):
        self.path = cache_path

    def save_object(self, obj, name):
        file = "{}/{}.pkl".format(self.path, name)
        with open(file, "wb") as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

    def fetch_object(self, name):
        file = "{}/{}.pkl".format(self.path, name)
        with open(file, "rb") as f:
            return pickle.load(f)

    def exists(self, name):
        file = "{}/{}.pkl".format(self.path, name)
        return os.path.exists(file)

    def clear(self):
        shutil.rmtree(self.path)
        os.mkdir(self.path)
