#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LIONZ Resources
---------------

This module contains utility functions and resources that are crucial for the operations of the LIONZ application.

LIONZ stands for Lesion segmentatION, a sophisticated solution for lesion segmentation tasks in medical imaging datasets. The resources module is designed to manage and provide auxiliary resources, such as configuration files, model weights, and other important artifacts necessary for the proper functioning of the application.

.. moduleauthor:: Lalith Kumar Shiyam Sundar <lalith.shiyamsundar@meduniwien.ac.at>
.. versionadded:: 0.1.0
"""
import logging

import torch
import SimpleITK as sitk
import numpy as np
from scipy.ndimage import label, sum as nd_sum
from lionz import constants

# List of available models in the LIONZ application
AVAILABLE_MODELS = ["fdg", "psma"]

# Dictionary of expected modalities for each model in the LIONZ application
EXPECTED_MODALITIES = {"fdg": ["PT", "CT"],
                       "psma": ["PT"]}

"""
TRACER_WORKFLOWS Dictionary Structure:

This dictionary organizes different workflows for various radiotracers used in PET and CT imaging.
The main goal is to facilitate the processing of different types of images based on their tracer and modality.

- Top-level keys represent different radiotracers, e.g., 'fdg', 'psma'.
- Each tracer has one or more 'workflows' associated with it.
- Each 'workflow' is represented by a key, e.g., 'pet_ct' or 'pet'.
- Inside each workflow, there's a 'channels' dictionary that specifies the image channels and their corresponding file
 extensions.

Structure:
{
    'tracer_name': {
        'workflows': {
            'workflow_name': {
                'channels': {
                    'channel_name': 'file_extension',
                    ...
                }
            },
            ...
        }
    },
    ...
}

Example:
For the 'fdg' tracer using the 'pet_ct' workflow:
- 'pet' images should have the file extension '0000.nii.gz'
- 'ct' images should have the file extension '0001.nii.gz'

This structure ensures modularity, making it easy to add new tracers, workflows, or modify existing ones.
"""

TRACER_WORKFLOWS = {
    'fdg': {
        'reference_modality': 'PT',
        'workflows': {
            'pet_ct': {
                'tumor_label': 11,
                'channels': {
                    'PT': '0000.nii.gz',
                    'CT': '0001.nii.gz'
                }
            },
            # 'pet': {
            #     'tumor_label': 11,  # Adjust this if the tumor label is different for the 'pet' workflow
            #     'channels': {
            #         'PT': '0000.nii.gz'
            #     }
            # }
        }
    },
    'psma': {
        'reference_modality': 'PT',  # You can change this for psma if needed
        'workflows': {
            'pet': {
                'channels': {
                    'PT': '0000.nii.gz'
                }
            }
        }
    }
}

# This dictionary holds the pre-trained models available in MooseZ library.
# Each key is a unique model identifier following a specific syntax mentioned above
# It should have the same name mentioned in AVAILABLE_MODELS list.
# Each value is a dictionary containing the following keys:
#    - url: The URL where the model files can be downloaded.
#    - filename: The filename of the model's zip file.
#    - directory: The directory where the model files will be extracted.
#    - trainer: The type of trainer used to train the model.
#    - voxel_spacing: The voxel spacing used in the model in the form [x, y, z], this is basically the median voxel
#    spacing generated by nnunetv2, and you can find this in the plans.json file of the model.
#    - multilabel_prefix: A prefix to distinguish between different types of labels in multi-label models.
#
# To include your own model, add a new entry to this dictionary following the above format.

MODELS = {
    "fdg": [
        {
            "url": "https://lionz.s3.eu.cloud-object-storage.appdomain.cloud/clin_pt_fdg_ct_2000epochs.zip",
            "filename": "Dataset789_Tumors_all_organs_LION.zip",
            "directory": "Dataset789_Tumors_all_organs_LION",
            "trainer": "nnUNetTrainerDA5_2000epochs",
            "voxel_spacing": [3, 3, 3],
            "multilabel_prefix": "fdg_tumor_01_"
        },
        {
            "url": "https://lionz.s3.eu.cloud-object-storage.appdomain.cloud/clin_pt_fdg_tumor_16082023.zip",
            "filename": "Dataset804_Tumors_all_organs.zip",
            "directory": "Dataset804_Tumors_all_organs",
            "trainer": "nnUNetTrainerDA5",
            "voxel_spacing": [3, 3, 3],
            "multilabel_prefix": "fdg_tumor_"
        }
    ],
    "psma": [
        {
            "url": "PLACEHOLDER_URL_FOR_MODEL",
            "filename": "PLACEHOLDER_FILENAME",
            "directory": "PLACEHOLDER_DIRECTORY",
            "trainer": "PLACEHOLDER_TRAINER",
            "voxel_spacing": ["PLACEHOLDER_X", "PLACEHOLDER_Y", "PLACEHOLDER_Z"],
            "multilabel_prefix": "PLACEHOLDER_PREFIX"
        }
    ],
    # Add more tracers as needed, following the same structure
}


def check_cuda() -> str:
    """
    This function checks if CUDA is available on the device and prints the device name and number of CUDA devices
    available on the device.

    Returns:
        str: The device to run predictions on, either "cpu" or "cuda".
    """
    if not torch.cuda.is_available():
        print(
            f"{constants.ANSI_ORANGE}CUDA not available on this device. Predictions will be run on CPU.{constants.ANSI_RESET}")
        return "cpu"
    else:
        device_count = torch.cuda.device_count()
        print(
            f"{constants.ANSI_GREEN} CUDA is available on this device with {device_count} GPU(s). Predictions will be run on GPU.{constants.ANSI_RESET}")
        return "cuda"


# This function maps the model name to the task number. This is the number that comes after Dataset in DatasetXXXX,
# after nnunetv2 training. If your model folder is Dataset123, then the task number is 123.
# It checks for known model names and returns the associated task number, this is ABSOLUTELY NEEDED for the moosez to
# work. If the provided model name doesn't match any known model, it raises an exception.

# When adding your own model, update this function to return the task number associated with your model.

def map_model_name_to_task_number(model_name: str) -> dict:
    """
    Maps the model name to the task number based on the workflow.
    :param model_name: The name of the model.
    :return: A dictionary of workflows and their associated task numbers.
    """
    if model_name == "fdg":
        return {'pet_ct': '789', 'pet': '804'}
    elif model_name == "psma":
        return {'workflow_name_placeholder': '444'}  # replace 'workflow_name_placeholder' with the actual workflow name
    else:
        raise Exception(f"Error: The model name '{model_name}' is not valid.")


def has_label_above_threshold(mask_path: str, threshold: int = 10) -> bool:
    """
    Check if the mask has non-zero voxels above a certain threshold after clearing a margin of the same size.

    Args:
        mask_path (str): Path to the mask image file.
        threshold (int): Number of voxels from the border to be set to zero and
                         minimum number of non-zero voxels needed.

    Returns:
        bool: True if the number of non-zero voxels (after clearing the margin) is above the threshold, False otherwise.
    """

    mask = sitk.ReadImage(mask_path)
    mask_array = sitk.GetArrayFromImage(mask)

    margin_padding = constants.MARGIN_SCALING_FACTOR * threshold

    # Flush voxels from the border to inside with zeros to avoid the edge artefacts
    mask_array[:margin_padding, :, :] = 0
    mask_array[-margin_padding:, :, :] = 0
    mask_array[:, :margin_padding, :] = 0
    mask_array[:, -margin_padding:, :] = 0
    mask_array[:, :, :margin_padding] = 0
    mask_array[:, :, -margin_padding:] = 0

    # Connected component analysis
    labeled_array, num_features = label(mask_array > 0)
    component_sizes = nd_sum(mask_array > 0, labeled_array, range(num_features + 1))

    # Mask out small components
    mask_size = mask_array > 0
    for index_size, component_size in enumerate(component_sizes):
        if component_size < threshold:
            mask_size[labeled_array == index_size] = False

    mask_array = mask_array * mask_size

    non_zero_voxel_count = np.sum(mask_array > 0)

    logging.info(
        f"Number of non-zero voxels after clearing a margin of {threshold} voxels and connected component analysis: {non_zero_voxel_count}")

    # If non-zero voxels are below the threshold, make the entire mask zero
    if non_zero_voxel_count < threshold:
        logging.info(f"Mask {mask_path} has less than {threshold} non-zero voxels. Flushing the mask with zero.")
        # Update the mask to have all zero values
        zero_mask = sitk.GetImageFromArray(np.zeros_like(mask_array))
        zero_mask.CopyInformation(mask)  # Copy metadata from the original mask
        sitk.WriteImage(zero_mask, mask_path)  # Overwrite the original mask with the blank one
        return False

    # If non-zero voxels are above the threshold, save the updated cleaned mask array
    logging.info(f"Mask {mask_path} has more than {threshold} non-zero voxels. Saving the updated mask after cleaning.")
    updated_mask = sitk.GetImageFromArray(mask_array)
    updated_mask.CopyInformation(mask)
    sitk.WriteImage(updated_mask, mask_path)

    return True


RULES = {
    "fdg": {
        'pet_ct': {
            'rule_func': (has_label_above_threshold, {"threshold": 10}),  # flush everything below 10 voxels
            #'action_on_true': 'delete_mask_and_continue',
            #'action_on_false': 'stop'
            'action_on_true': 'stop',
            'action_on_false': 'stop'
        },
        # 'pet': {
        #     'rule_func': (has_label_above_threshold, {"threshold": 10}),
        #     'action_on_true': 'continue',
        #     'action_on_false': 'continue'
        # }
    }
    # Add more rules for different tracers and workflows as necessary.
}
