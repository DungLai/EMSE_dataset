# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import re


def url(text):
    pattern_reference_url = re.compile(
        r"http[s]?://(hg.mozilla|searchfox|dxr.mozilla)\S+"
    )
    pattern_url = re.compile(r"http\S+")
    return pattern_url.sub(
        "__URL__", pattern_reference_url.sub("__CODE_REFERENCE_URL__", text)
    )


def fileref(text):
    pattern = re.compile(
        r"\w+\.py\b|\w+\.json\b|\w+\.js\b|\w+\.jsm\b|\w+\.html\b|\w+\.css\b|\w+\.c\b|\w+\.cpp\b|\w+\.h\b"
    )
    return pattern.sub("__FILE_REFERENCE__", text)


def responses(text):
    pattern = re.compile(">[^\n]+")
    return pattern.sub(" ", text)


def hex(text):
    pattern = re.compile(r"\b0[xX][0-9a-fA-F]+\b")
    return pattern.sub("__HEX_NUMBER__", text)


FIREFOX_DLLS_MATCH = "|".join(
    [
        "libmozwayland.so",
        "libssl3.so",
        "libnssdbm3.so",
        "liblgpllibs.so",
        "libmozavutil.so",
        "libxul.so",
        "libmozgtk.so",
        "libnssckbi.so",
        "libclearkey.dylib",
        "libmozsqlite3.so",
        "libplc4.so",
        "libsmime3.so",
        "libclearkey.so",
        "libnssutil3.so",
        "libnss3.so",
        "libplds4.so",
        "libfreeblpriv3.so",
        "libsoftokn3.so",
        "libmozgtk.so",
        "libmozavcodec.so",
        "libnspr4.so",
        "IA2Marshal.dll",
        "lgpllibs.dll",
        "libEGL.dll",
        "libGLESv2.dll",
        "libmozsandbox.so",
        "AccessibleHandler.dll",
        "AccessibleMarshal.dll",
        "api-ms-win-core-console-l1-1-0.dll",
        "api-ms-win-core-datetime-l1-1-0.dll",
        "api-ms-win-core-debug-l1-1-0.dll",
        "api-ms-win-core-errorhandling-l1-1-0.dll",
        "api-ms-win-core-file-l1-1-0.dll",
        "api-ms-win-core-file-l1-2-0.dll",
        "api-ms-win-core-file-l2-1-0.dll",
        "api-ms-win-core-handle-l1-1-0.dll",
        "api-ms-win-core-heap-l1-1-0.dll",
        "api-ms-win-core-interlocked-l1-1-0.dll",
        "api-ms-win-core-libraryloader-l1-1-0.dll",
        "api-ms-win-core-localization-l1-2-0.dll",
        "api-ms-win-core-memory-l1-1-0.dll",
        "api-ms-win-core-namedpipe-l1-1-0.dll",
        "api-ms-win-core-processenvironment-l1-1-0.dll",
        "api-ms-win-core-processthreads-l1-1-0.dll",
        "api-ms-win-core-processthreads-l1-1-1.dll",
        "api-ms-win-core-profile-l1-1-0.dll",
        "api-ms-win-core-rtlsupport-l1-1-0.dll",
        "api-ms-win-core-string-l1-1-0.dll",
        "api-ms-win-core-synch-l1-1-0.dll",
        "api-ms-win-core-synch-l1-2-0.dll",
        "api-ms-win-core-sysinfo-l1-1-0.dll",
        "api-ms-win-core-timezone-l1-1-0.dll",
        "api-ms-win-core-util-l1-1-0.dll",
        "api-ms-win-crt-conio-l1-1-0.dll",
        "api-ms-win-crt-convert-l1-1-0.dll",
        "api-ms-win-crt-environment-l1-1-0.dll",
        "api-ms-win-crt-filesystem-l1-1-0.dll",
        "api-ms-win-crt-heap-l1-1-0.dll",
        "api-ms-win-crt-locale-l1-1-0.dll",
        "api-ms-win-crt-math-l1-1-0.dll",
        "api-ms-win-crt-multibyte-l1-1-0.dll",
        "api-ms-win-crt-private-l1-1-0.dll",
        "api-ms-win-crt-process-l1-1-0.dll",
        "api-ms-win-crt-runtime-l1-1-0.dll",
        "api-ms-win-crt-stdio-l1-1-0.dll",
        "api-ms-win-crt-string-l1-1-0.dll",
        "api-ms-win-crt-time-l1-1-0.dll",
        "api-ms-win-crt-utility-l1-1-0.dll",
        "d3dcompiler_47.dll",
        "freebl3.dll",
        "mozavcodec.dll",
        "mozavutil.dll",
        "mozglue.dll",
        "msvcp140.dll",
        "nss3.dll",
        "nssckbi.dll",
        "nssdbm3.dll",
        "qipcap64.dll",
        "softokn3.dll",
        "ucrtbase.dll",
        "vcruntime140.dll",
        "xul.dll",
        "clearkey.dll",
        "libfreebl3.dylib",
        "liblgpllibs.dylib",
        "libmozavcodec.dylib",
        "libmozavutil.dylib",
        "libmozglue.dylib",
        "libnss3.dylib",
        "libnssckbi.dylib",
        "libnssdbm3.dylib",
        "libplugin_child_interpose.dylib",
        "libsoftokn3.dylib",
    ]
).replace(".", r"\.")


def dll(text):
    regex = re.compile(fr"\b(?!{FIREFOX_DLLS_MATCH})\w+(\.dll|\.so|\.dylib)\b")
    return regex.sub("__DLL_NAME__", text)


def synonyms(text):
    synonyms = [
        ("safemode", ["safemode", "safe mode"]),
        ("str", ["str", "steps to reproduce", "repro steps"]),
        ("uaf", ["uaf", "use after free", "use-after-free"]),
        ("asan", ["asan", "address sanitizer", "addresssanitizer"]),
        (
            "permafailure",
            [
                "permafailure",
                "permafailing",
                "permafail",
                "perma failure",
                "perma failing",
                "perma fail",
                "perma-failure",
                "perma-failing",
                "perma-fail",
            ],
        ),
        ("spec", ["spec", "specification"]),
    ]

    for synonym_group, synonym_list in synonyms:
        pattern = re.compile(
            "|".join(fr"\b{synonym}\b" for synonym in synonym_list), flags=re.IGNORECASE
        )
        text = pattern.sub(synonym_group, text)

    return text


def crash(text):
    pattern = re.compile(
        r"bp-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{6}[0-9]{6}\b"
    )
    return pattern.sub("__CRASH_STATS_LINK__", text)
