import collections
import os
import warnings

import h5py
from torch.utils.data import Dataset
import numpy as np

import models.coordconv
from utils.utils import get_key_def, get_key_recursive


def create_files_and_datasets(params, samples_folder):
    """
    Function to create the hdfs files (trn, val and tst).
    :param params: (dict) Parameters found in the yaml config file.
    :param samples_folder: (str) Path to the output folder.
    :return: (hdf5 datasets) trn, val ant tst datasets.
    """
    samples_size = params['global']['samples_size']
    number_of_bands = params['global']['number_of_bands']
    meta_map = get_key_def('meta_map', params['global'], {})
    real_num_bands = number_of_bands - MetaSegmentationDataset.get_meta_layer_count(meta_map)
    assert real_num_bands > 0, "invalid number of bands when accounting for meta layers"
    hdf5_files = []
    for subset in ["trn", "val", "tst"]:
        hdf5_file = h5py.File(os.path.join(samples_folder, f"{subset}_samples.hdf5"), "w")
        hdf5_file.create_dataset("sat_img", (0, samples_size, samples_size, real_num_bands), np.float32,
                                 maxshape=(None, samples_size, samples_size, real_num_bands))
        hdf5_file.create_dataset("map_img", (0, samples_size, samples_size), np.int16,
                                 maxshape=(None, samples_size, samples_size))
        hdf5_file.create_dataset("meta_idx", (0, 1), dtype=np.int16, maxshape=(None, 1))
        try:
            hdf5_file.create_dataset("metadata", (0, 1), dtype=h5py.string_dtype(), maxshape=(None, 1))
        except AttributeError as e:
            warnings.warn(f'Ignoring error: {e}. Make sure no metadata is used or update h5py to version 2.10 or higher')
        hdf5_files.append(hdf5_file)
    return hdf5_files


class SegmentationDataset(Dataset):
    """Semantic segmentation dataset based on HDF5 parsing."""

    def __init__(self, work_folder, dataset_type, max_sample_count=None, dontcare=None, transform=None):
        # note: if 'max_sample_count' is None, then it will be read from the dataset at runtime
        self.work_folder = work_folder
        self.max_sample_count = max_sample_count
        self.dataset_type = dataset_type
        self.transform = transform
        self.metadata = []
        self.dontcare = dontcare
        self.hdf5_path = os.path.join(self.work_folder, self.dataset_type + "_samples.hdf5")
        with h5py.File(self.hdf5_path, "r") as hdf5_file:
            if "metadata" in hdf5_file:
                for i in range(hdf5_file["metadata"].shape[0]):
                    metadata = hdf5_file["metadata"][i, ...]
                    if isinstance(metadata, np.ndarray) and len(metadata) == 1:
                        metadata = metadata[0]
                    if isinstance(metadata, str):
                        if "ordereddict" in metadata:
                            metadata = metadata.replace("ordereddict", "collections.OrderedDict")
                        if metadata.startswith("collections.OrderedDict"):
                            metadata = eval(metadata)
                    self.metadata.append(metadata)
            if self.max_sample_count is None:
                self.max_sample_count = hdf5_file["sat_img"].shape[0]

    def __len__(self):
        return self.max_sample_count

    def _remap_labels(self, map_img):
        # note: will do nothing if 'dontcare' is not set in constructor, or set to non-zero value
        if self.dontcare is None or self.dontcare != 0:
            return map_img
        # for now, the current implementation only handles the original 'dontcare' value as zero
        # to keep the impl simple, we just reduce all indices by one so that 'dontcare' becomes -1
        assert map_img.dtype == np.int8 or map_img.dtype == np.int16 or map_img.dtype == np.int32
        map_img -= 1
        return map_img

    def __getitem__(self, index):
        with h5py.File(self.hdf5_path, "r") as hdf5_file:
            sat_img = hdf5_file["sat_img"][index, ...]
            map_img = self._remap_labels(hdf5_file["map_img"][index, ...])
            meta_idx = int(hdf5_file["meta_idx"][index]) if "meta_idx" in hdf5_file else -1
            metadata = None
            if meta_idx != -1:
                metadata = self.metadata[meta_idx]
        sample = {"sat_img": sat_img, "map_img": map_img, "metadata": metadata}
        if self.transform:
            sample = self.transform(sample)
        return sample


class MetaSegmentationDataset(SegmentationDataset):
    """Semantic segmentation dataset interface that appends metadata under new tensor layers."""

    metadata_handling_modes = ["const_channel", "scaled_channel"]

    def __init__(self, work_folder, dataset_type, meta_map, max_sample_count=None, dontcare=None, transform=None):
        assert meta_map is None or isinstance(meta_map, dict), "unexpected metadata mapping object type"
        assert meta_map is None or all([isinstance(k, str) and v in self.metadata_handling_modes for k, v in meta_map.items()]), \
            "unexpected metadata key type or value handling mode"
        super().__init__(work_folder=work_folder, dataset_type=dataset_type, max_sample_count=max_sample_count,
                         dontcare=dontcare, transform=transform)
        assert all([isinstance(m, (dict, collections.OrderedDict)) for m in self.metadata]), \
            "cannot use provided metadata object type with meta-mapping dataset interface"
        self.meta_map = meta_map

    @staticmethod
    def append_meta_layers(tensor, meta_map, metadata):
        if meta_map:
            assert isinstance(metadata, (dict, collections.OrderedDict)), "unexpected metadata type"
            for meta_key, mode in meta_map.items():
                meta_val = get_key_recursive(meta_key, metadata)
                if mode == "const_channel":
                    assert np.isscalar(meta_val), "constant channel-wise assignment requires scalar value"
                    layer = np.full(tensor.shape[0:2], meta_val, dtype=np.float32)
                    tensor = np.insert(tensor, tensor.shape[2], layer, axis=2)
                elif mode == "scaled_channel":
                    assert np.isscalar(meta_val), "scaled channel-wise coords assignment requires scalar value"
                    layers = models.coordconv.get_coords_map(tensor.shape[0], tensor.shape[1]) * meta_val
                    tensor = np.insert(tensor, tensor.shape[2], layers, axis=2)
                # else...
        return tensor

    @staticmethod
    def get_meta_layer_count(meta_map):
        meta_layers = 0
        if meta_map:
            for meta_key, mode in meta_map.items():
                if mode == "const_channel":
                    meta_layers += 1
                elif mode == "scaled_channel":
                    meta_layers += 2
        return meta_layers

    def __getitem__(self, index):
        # put metadata layer in util func for inf script?
        with h5py.File(self.hdf5_path, "r") as hdf5_file:
            sat_img = hdf5_file["sat_img"][index, ...]
            map_img = self._remap_labels(hdf5_file["map_img"][index, ...])
            meta_idx = int(hdf5_file["meta_idx"][index]) if "meta_idx" in hdf5_file else -1
            assert meta_idx != -1, f"metadata unvailable in sample #{index}"
            sat_img = self.append_meta_layers(sat_img, self.meta_map, self.metadata[meta_idx])
        sample = {"sat_img": sat_img, "map_img": map_img, "metadata": self.metadata[meta_idx]}
        if self.transform:
            sample = self.transform(sample)
        return sample
