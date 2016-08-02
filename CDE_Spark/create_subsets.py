import numpy as np


def create_subsets(adaf_objs):
    subsets = {}
    for adaf_obj in adaf_objs:
        file_name_field0 = adaf_obj.meta["FILENAME_field_0"].value()[0]
        if not file_name_field0 in subsets.keys():
            subsets[file_name_field0] = []
        subsets[file_name_field0].append(adaf_obj)

    # update meta
    subsets_list = []
    for field0, subset in subsets.items():
        for adaf_obj in subset:
            adaf_obj.meta.create_column("DATASET_subgroup", np.array(["FILENAME_field_0: {}".format(field0)]))
        subsets_list.append(subset)
    return subsets_list


