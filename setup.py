#!/usr/bin/env python3
"""
Compile CUDA source code and setup Python 3 package 'nipet'
for namespace 'niftypet'.
"""
import logging
import os
import platform
import re
import sys
from textwrap import dedent

from setuptools import find_packages
from skbuild import setup

from niftypet.ninst import cudasetup as cs
from niftypet.ninst import dinf
from niftypet.ninst import install_tools as tls

__author__ = ("Pawel J. Markiewicz", "Casper O. da Costa-Luis")
__copyright__ = "Copyright 2020"
__licence__ = __license__ = "Apache 2.0"

logging.basicConfig(level=logging.INFO, format=tls.LOG_FORMAT)
log = logging.getLogger("nipet.setup")

tls.check_platform()

# =================================================================================================
# automatically detects if the CUDA header files are in agreement with Python constants.
# =================================================================================================


def chck_vox_h(Cnt):
    """check if voxel size in Cnt and adjust the CUDA header files accordingly."""
    rflg = False
    path_current = os.path.dirname(os.path.realpath(__file__))
    fpth = os.path.join(path_current, "niftypet", "nipet", "include", "def.h")
    with open(fpth, "r") as fd:
        def_h = fd.read()
    # get the region of keeping in synch with Python
    i0 = def_h.find("//## start ##//")
    i1 = def_h.find("//## end ##//")
    defh = def_h[i0:i1]
    # list of constants which will be kept in synch from Python
    cnt_list = ["SZ_IMX", "SZ_IMY", "SZ_IMZ", "TFOV2", "SZ_VOXY", "SZ_VOXZ", "SZ_VOXZi"]
    flg = False
    for s in cnt_list:
        m = re.search("(?<=#define " + s + r")\s*\d*\.*\d*", defh)
        if s[3] == "V":
            # print(s, float(m.group(0)), Cnt[s])
            if Cnt[s] != float(m.group(0)):
                flg = True
                break
        else:
            # print(s, int(m.group(0)), Cnt[s])
            if Cnt[s] != int(m.group(0)):
                flg = True
                break
    # if flag is set then redefine the constants in the sct.h file
    if flg:
        strNew = (
            "//## start ##// constants definitions in synch with Python.   DON"
            "T MODIFY MANUALLY HERE!\n"
            + "// IMAGE SIZE\n"
            + "// SZ_I* are image sizes\n"
            + "// SZ_V* are voxel sizes\n"
        )
        strDef = "#define "
        for s in cnt_list:
            strNew += strDef + s + " " + str(Cnt[s]) + (s[3] == "V") * "f" + "\n"

        scthNew = def_h[:i0] + strNew + def_h[i1:]
        with open(fpth, "w") as fd:
            fd.write(scthNew)
        rflg = True

    return rflg


def chck_sct_h(Cnt):
    """
    check if voxel size for scatter correction changed and adjust
    the CUDA header files accordingly.
    """
    rflg = False
    path_current = os.path.dirname(os.path.realpath(__file__))
    fpth = os.path.join(path_current, "niftypet", "nipet", "sct", "src", "sct.h")
    # pthcmpl = os.path.dirname(resource_filename(__name__, ''))
    with open(fpth, "r") as fd:
        sct_h = fd.read()
    # get the region of keeping in synch with Python
    i0 = sct_h.find("//## start ##//")
    i1 = sct_h.find("//## end ##//")
    scth = sct_h[i0:i1]
    # list of constants which will be kept in sych from Python
    cnt_list = [
        "SS_IMX",
        "SS_IMY",
        "SS_IMZ",
        "SSE_IMX",
        "SSE_IMY",
        "SSE_IMZ",
        "NCOS",
        "SS_VXY",
        "SS_VXZ",
        "IS_VXZ",
        "SSE_VXY",
        "SSE_VXZ",
        "R_RING",
        "R_2",
        "IR_RING",
        "SRFCRS",
    ]
    flg = False
    for i, s in enumerate(cnt_list):
        m = re.search("(?<=#define " + s + r")\s*\d*\.*\d*", scth)
        # if s[-3]=='V':
        if i < 7:
            # print(s, int(m.group(0)), Cnt[s])
            if Cnt[s] != int(m.group(0)):
                flg = True
                break
        else:
            # print(s, float(m.group(0)), Cnt[s])
            if Cnt[s] != float(m.group(0)):
                flg = True
                break

    # if flag is set then redefine the constants in the sct.h file
    if flg:
        strNew = dedent(
            """\
            //## start ##// constants definitions in synch with Python.   DO NOT MODIFY!\n
            // SCATTER IMAGE SIZE AND PROPERTIES
            // SS_* are used for the mu-map in scatter calculations
            // SSE_* are used for the emission image in scatter calculations
            // R_RING, R_2, IR_RING are ring radius, squared radius and inverse of the radius, respectively.
            // NCOS is the number of samples for scatter angular sampling
            """
        )

        strDef = "#define "
        for i, s in enumerate(cnt_list):
            strNew += strDef + s + " " + str(Cnt[s]) + (i > 6) * "f" + "\n"

        scthNew = sct_h[:i0] + strNew + sct_h[i1:]
        with open(fpth, "w") as fd:
            fd.write(scthNew)
        # sys.path.append(pthcmpl)
        rflg = True

    return rflg


def check_constants():
    """get the constants for the mMR from the resources file before
    getting the path to the local resources.py (on Linux machines it is in ~/.niftypet)"""
    resources = cs.get_resources()
    Cnt = resources.get_mmr_constants()

    sct_compile = chck_sct_h(Cnt)
    def_compile = chck_vox_h(Cnt)
    # sct_compile = False
    # def_compile = False

    if sct_compile or def_compile:
        txt = "NiftyPET constants were changed: needs CUDA compilation."
    else:
        txt = "- - . - -"

    log.info(
        dedent(
            """\
            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            changed sct.h: {}
            changed def.h: {}
            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            {}
            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""
        ).format(sct_compile, def_compile, txt)
    )


cs.resources_setup(gpu=False)  # install resources.py
# check and update the constants in C headers according to resources.py
check_constants()
gpuarch = cs.dev_setup()  # update resources.py with a supported GPU device


log.info(
    dedent(
        """\
        --------------------------------------------------------------
        Finding hardware mu-maps
        --------------------------------------------------------------"""
    )
)
# get the local path to NiftyPET resources.py
path_resources = cs.path_niftypet_local()
# if exists, import the resources and get the constants
resources = cs.get_resources()
# get the current setup, if any
Cnt = resources.get_setup()

# assume the hardware mu-maps are not installed
hmu_flg = False
# go through each piece of the hardware components
if "HMUDIR" in Cnt and Cnt["HMUDIR"] != "":
    for hi in Cnt["HMULIST"]:
        if os.path.isfile(os.path.join(Cnt["HMUDIR"], hi)):
            hmu_flg = True
        else:
            hmu_flg = False
            break
# if not installed ask for the folder through GUI
# otherwise the path will have to be filled manually
if not hmu_flg:
    prompt = dict(
        title="Folder for hardware mu-maps: ", initialdir=os.path.expanduser("~")
    )
    if not os.getenv("DISPLAY", False):
        prompt["name"] = "HMUDIR"
    Cnt["HMUDIR"] = tls.askdirectory(**prompt)
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# update the path in resources.py
tls.update_resources(Cnt)
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
log.info("hardware mu-maps have been located")

cmake_args = [f"-DPython3_ROOT_DIR={sys.prefix}"]
nvcc_arches = {"{2:d}{3:d}".format(*i) for i in dinf.gpuinfo()}
cmake_args.append("-DCMAKE_CUDA_ARCHITECTURES=" + " ".join(sorted(nvcc_arches)))
setup(
    version="2.0.0",
    packages=find_packages(exclude=["examples", "tests"]),
    package_data={"niftypet": ["nipet/auxdata/*"]},
    cmake_source_dir="niftypet",
    cmake_languages=("C", "CXX", "CUDA"),
    cmake_minimum_required_version="3.18",
    cmake_args=cmake_args,
)
