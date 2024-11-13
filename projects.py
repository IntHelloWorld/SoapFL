import os
import shutil

SBF = {
    "Closure": ([44, 51, 55, 61, 101, 119, 159, 160], [], "None"),
    "Codec": ([4], [], "None"),
    "Compress": ([13, 39], [], "None"),
    "Csv": ([1, 10], [], "None"),
    "Imaging": ([3, 4, 6, 11, 14], [], "None"),
    "JacksonDatabind": ([1, 8, 9, 12, 16, 17, 19, 24, 33, 35, 42, 46, 125], [], "None"),
    "JacksonXml": ([3], [], "None"),
    "Mockito": ([13, 34], [], "None"),
    "Jsoup": ([8, 26, 51, 53, 70, 72], [], "None"),
    "HttpClient5": ([5], [], "httpclient5"),
    "Pdfbox_pdfbox": ([1, 3], [], "pdfbox"),
    "JavaClassmate": ([1, 2], [], "None"),
    "Woodstox": ([3, 4, 5], [], "None"),
    "MetaModel_core": ([3], [], "core"),
    "Mrunit": ([1], [], "None"),
    "Zip4j": ([2, 3, 5, 8], [], "None"),
    "Jdbm3": ([3], [], "None"),
    "Restfixture": ([2], [], "None"),
    "Jcabi_http": ([2, 13], [], "None"),
}

SBF = {
    "Closure": ([44], [], "None"),
    "Codec": ([4], [], "None"),
    "Imaging": ([3], [], "None"),
    "JacksonDatabind": ([1], [], "None"),
    "JacksonXml": ([3], [], "None"),
    "Mockito": ([13], [], "None"),
    "Jsoup": ([8], [], "None"),
    "HttpClient5": ([5], [], "httpclient5"),
    "JavaClassmate": ([1], [], "None"),
    "Woodstox": ([3, 4], [], "None"),
    "Restfixture": ([2], [], "None"),
    "Jcabi_http": ([2], [], "None"),
}

projectDict = {
    "IO": ([1, 2], [], "None")
}

ALL_BUGS = projectDict