import os
import pickle
import shutil


class Cache:
    def __init__(self, cache_path):
        self.path = cache_path

    def save_object(self, name: str, obj, sub_dir=None):
        final_dir = self._get_final_dir(sub_dir)
        self._create_dir(final_dir)
        file = "{}/{}.pkl".format(final_dir, name)
        with open(file, "wb") as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

    def fetch_object(self, name: str, sub_dir=None):
        file = "{}/{}.pkl".format(self._get_final_dir(sub_dir), name)
        with open(file, "rb") as f:
            return pickle.load(f)

    def exists(self, name: str, sub_dir=None):
        file = "{}/{}.pkl".format(self._get_final_dir(sub_dir), name)
        return os.path.exists(file)

    def clear(self):
        shutil.rmtree(self.path)
        os.mkdir(self.path)

    def _get_final_dir(self, sub_dir: str):
        if not sub_dir:
            return self.path
        return "{}/{}".format(self.path, sub_dir)

    @staticmethod
    def _create_dir(path: str):
        os.makedirs(path, exist_ok=True)
