# -*- coding: utf-8 -*-
"""Generate restructuredtext file of Input information to be inserted into the manual"""

import sys

import os

sys.path.append(os.path.abspath(os.path.join(__file__, "../../..")))

from collections import OrderedDict

from mycodo.config import INSTALL_DIRECTORY
from mycodo.utils.inputs import parse_input_information

save_path = os.path.join(INSTALL_DIRECTORY, "mycodo-inputs.rst")

inputs_info = OrderedDict()
mycodo_info = OrderedDict()

def repeat_to_length(s, wanted):
    return (s * (wanted//len(s) + 1))[:wanted]

for input_id, input_data in parse_input_information().items():
    name_str = ""
    if 'input_manufacturer' in input_data and input_data['input_manufacturer']:
        name_str += "{}".format(input_data['input_manufacturer'])
    if 'input_name' in input_data and input_data['input_name']:
        name_str += ": {}".format(input_data['input_name'])
    if 'measurements_name' in input_data and input_data['measurements_name']:
        name_str += ": {}".format(input_data['measurements_name'])

    if ('input_manufacturer' in input_data and
            input_data['input_manufacturer'] in ['Linux', 'Mycodo', 'Raspberry Pi', 'System']):
        if name_str in mycodo_info and 'input_library' in mycodo_info[name_str]:
            # Multiple libraries, append library
            mycodo_info[name_str]['input_library'].append(input_data['input_library'])
        else:
            # Only one library
            mycodo_info[name_str] = input_data
            if 'input_library' in input_data:
                mycodo_info[name_str]['input_library'] = [input_data['input_library']]  # turn into list
    else:
        if name_str in inputs_info and 'input_library' in inputs_info[name_str]:
            # Multiple libraries, append library
            inputs_info[name_str]['input_library'].append(input_data['input_library'])
        else:
            # Only one library
            inputs_info[name_str] = input_data
            if 'input_library' in input_data:
                inputs_info[name_str]['input_library'] = [input_data['input_library']]  # turn into list

mycodo_info = dict(OrderedDict(sorted(mycodo_info.items(), key = lambda t: t[0])))
inputs_info = dict(OrderedDict(sorted(inputs_info.items(), key = lambda t: t[0])))

list_inputs = [
    (mycodo_info, "Built-In Inputs (System-Specific)"),
    (inputs_info, "Built-In Inputs (Sensors)")
]

with open(save_path, 'w') as out_file:
    out_file.write("\n")
    for each_list in list_inputs:
        out_file.write("{}\n".format(each_list[1]))
        out_file.write("{}\n\n".format(repeat_to_length("~", len(each_list[1]))))

        for each_id, each_data in each_list[0].items():
            name_str = ""
            if 'input_manufacturer' in each_data and each_data['input_manufacturer']:
                name_str += "{}".format(each_data['input_manufacturer'])
            if 'input_name' in each_data and each_data['input_name']:
                name_str += ": {}".format(each_data['input_name'])

            out_file.write("{}\n".format(name_str))
            out_file.write("{}\n\n".format(repeat_to_length("^", len(name_str))))

            if 'measurements_name' in each_data and each_data['measurements_name']:
                out_file.write("| Measurements: {}\n".format(each_data['measurements_name']))

            if 'input_library' in each_data and each_data['input_library']:
                out_file.write("| Libraries: ")
                for i, each_lib in enumerate(each_data['input_library']):
                    if len(each_data['input_library']) == 1:
                        out_file.write(each_lib)
                    else:
                        out_file.write("Input Module {num}: {lib}".format(num=i + 1, lib=each_lib))
                    if i + 1 < len(each_data['input_library']):
                        out_file.write("; ")
                    else:
                        out_file.write("\n")

            if 'url_manufacturer' in each_data and each_data['url_manufacturer']:
                out_file.write("| Manufacturer URL(s): ")
                for i, each_url in enumerate(each_data['url_manufacturer']):
                    out_file.write("`Link {num} <{url}>`__".format(num=i + 1, url=each_url))
                    if i + 1 < len(each_data['url_manufacturer']):
                        out_file.write(", ")
                    else:
                        out_file.write("\n")

            if 'url_datasheet' in each_data and each_data['url_datasheet']:
                out_file.write("| Datasheet URL(s): ")
                for i, each_url in enumerate(each_data['url_datasheet']):
                    out_file.write("`Link {num} <{url}>`__".format(num=i + 1, url=each_url))
                    if i + 1 < len(each_data['url_datasheet']):
                        out_file.write(", ")
                    else:
                        out_file.write("\n")

            if 'url_product_purchase' in each_data and each_data['url_product_purchase']:
                out_file.write("| Product URL(s): ")
                for i, each_url in enumerate(each_data['url_product_purchase']):
                    out_file.write("`Link {num} <{url}>`__".format(num=i + 1, url=each_url))
                    if i + 1 < len(each_data['url_product_purchase']):
                        out_file.write(", ")
                    else:
                        out_file.write("\n")

            if 'message' in each_data and each_data['message']:
                out_file.write("\n{}\n".format(each_data['message']))

            out_file.write("\n")
