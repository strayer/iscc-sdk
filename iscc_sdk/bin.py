# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from platform import system, architecture
from urllib.parse import urlparse
from urllib.request import urlretrieve
from blake3 import blake3
from loguru import logger as log
import stat
import jdk
import iscc_sdk as idk
from concurrent.futures import ThreadPoolExecutor

BASE_VERSION = "1.0.0"
BASE_URL = f"https://github.com/iscc/iscc-binaries/releases/download/v{BASE_VERSION}"

FFPROBE_VERSION = "4.4.1"
FFPROBE_URLS = {
    "windows-64": f"{BASE_URL}/ffprobe-{FFPROBE_VERSION}-win-64.zip",
    "linux-64": f"{BASE_URL}/ffprobe-{FFPROBE_VERSION}-linux-64.zip",
    "darwin-64": f"{BASE_URL}/ffprobe-{FFPROBE_VERSION}-osx-64.zip",
}
FFPROBE_CHECKSUMS = {
    "windows-64": "6c6c7d49465f70f3a4c60dc2d5aeddb4049527c82ee6e2b4c6ad0a2a9fc9188e",
    "linux-64": "bfa86d00341cacbbcaad6c38c706ad1df9f268b1d1e5a1f19206ab47a95aad8f",
    "darwin-64": "1904fdf6d0250e3c44aa5f44b0bf31033b40329f1c3e51d3d06438273174506d",
}


FFMPEG_VERSION = "4.4.1"
FFMPEG_URLS = {
    "windows-64": f"{BASE_URL}/ffmpeg-{FFMPEG_VERSION}-win-64.zip",
    "linux-64": f"{BASE_URL}/ffmpeg-{FFMPEG_VERSION}-linux-64.zip",
    "darwin-64": f"{BASE_URL}/ffmpeg-{FFMPEG_VERSION}-osx-64.zip",
}
FFMPEG_CHECKSUMS = {
    "windows-64": "b77405ee98580971cb36c4ca0c7f888283dcffc347c282b304abbb3c1eee6fc2",
    "linux-64": "a8ac9f1e28ad31ca366dba17dd0c486926d533d76ffc9b47a976308245ab064e",
    "darwin-64": "33f980b5b59ddfc663170a419110e9504527c092b21ba6592c525f7a7c183887",
}

FPCALC_VERSION = "1.5.1"
FPCALC_URLS = {
    "windows-64": f"{BASE_URL}/chromaprint-fpcalc-{FPCALC_VERSION}-windows-x86_64.zip",
    "linux-64": f"{BASE_URL}/chromaprint-fpcalc-{FPCALC_VERSION}-linux-x86_64.tar.gz",
    "darwin-64": f"{BASE_URL}/chromaprint-fpcalc-{FPCALC_VERSION}-macos-x86_64.tar.gz",
}
FPCALC_CHECKSUMS = {
    "windows-64": "e29364a879ddf7bea403b0474a556e43f40d525e0d8d5adb81578f1fbf16d9ba",
    "linux-64": "190977d9419daed8a555240b9c6ddf6a12940c5ff470647095ee6242e217de5c",
    "darwin-64": "afea164b0bc9b91e5205d126f96a21836a91ea2d24200e1b7612a7304ea3b4f1",
}

TIKA_VERSION = "2.3.0"
TIKA_URL = f"{BASE_URL}/tika-app-{TIKA_VERSION}.jar"
TIKA_CHECKSUM = "e3f6ff0841b9014333fc6de4b849704384abf362100edfa573a6e4104b654491"

EXIV2_VERSION = "0.27.5"
EXIV2_URLS = {
    "windows-64": f"{BASE_URL}/exiv2-{EXIV2_VERSION}-2019msvc64.zip",
    "linux-64": f"{BASE_URL}/exiv2-{EXIV2_VERSION}-Linux64.tar.gz",
    "darwin-64": f"{BASE_URL}/exiv2-{EXIV2_VERSION}-Darwin.tar.gz",
}

EXIV2_CHECKSUMS = {
    "windows-64": "3e00112648ed98a60a381fc3c6dd10ec263b1d56dec4f07dce86a7736517ebcd",
    "linux-64": "6c6339f7f575ed794c4669e7eab4ef400a6cf7981f78ea26fc985d24d9620d58",
    "darwin-64": "aaf574fa910721fdc653519a2ca8ecf3d4e9b06213167ad630fcb9e18d329af4",
}

EXIV2_RELPATH = {
    "windows-64": f"exiv2-{EXIV2_VERSION}-2019msvc64/bin/exiv2.exe",
    "linux-64": f"exiv2-{EXIV2_VERSION}-Linux64/bin/exiv2",
    "darwin-64": f"exiv2-{EXIV2_VERSION}-Darwin/bin/exiv2",
}

EXIV2JSON_RELPATH = {
    "windows-64": f"exiv2-{EXIV2_VERSION}-2019msvc64/bin/exiv2json.exe",
    "linux-64": f"exiv2-{EXIV2_VERSION}-Linux64/bin/exiv2json",
    "darwin-64": f"exiv2-{EXIV2_VERSION}-Darwin/bin/exiv2json",
}


def install():
    """Install binary tools for content extraction"""
    with ThreadPoolExecutor(max_workers=5) as p:
        p.submit(exiv2_install)
        p.submit(fpcalc_install)
        p.submit(ffprobe_install)
        p.submit(ffmpeg_install)
        p.submit(tika_install)
    return True


def system_tag():
    os_tag = system().lower()
    os_bits = architecture()[0].rstrip("bit")
    return f"{os_tag}-{os_bits}"


def is_installed(fp: str) -> bool:
    """Check if binary at `fp` exists and is executable"""
    return os.path.isfile(fp) and os.access(fp, os.X_OK)


########################################################################################
# Exiv2                                                                                #
########################################################################################


def exiv2_download_url() -> str:
    """Return system and version dependant exiv2 download url"""
    return EXIV2_URLS[system_tag()]


def exiv2_bin() -> str:
    """Returns local path to exiv2 executable."""
    return os.path.join(idk.dirs.user_data_dir, EXIV2_RELPATH[system_tag()])


def exiv2json_bin() -> str:
    return os.path.join(idk.dirs.user_data_dir, EXIV2JSON_RELPATH[system_tag()])


def exiv2_is_installed():  # pragma: no cover
    """Check if exiv2 is installed"""
    fp = exiv2_bin()
    return os.path.isfile(fp) and os.access(fp, os.X_OK)


def exiv2_download():  # pragma: no cover
    b3 = EXIV2_CHECKSUMS[system_tag()]
    return download_file(exiv2_download_url(), checksum=b3)


def exiv2_extract(archive):  # pragma: no cover

    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive, "r") as zip_file:
            zip_file.extractall(Path(archive).parent.absolute())

    elif archive.endswith("tar.gz"):
        with tarfile.open(archive, "r:gz") as tar_file:
            tar_file.extractall(Path(archive).parent.absolute())


def exiv2_install():  # pragma: no cover
    """Install exiv2 command line tool and return path to executable."""
    if exiv2_is_installed():
        log.debug("Exiv2 is already installed.")
        return exiv2_bin()
    log.critical("installing exiv2")
    archive_path = exiv2_download()
    exiv2_extract(archive_path)
    st = os.stat(exiv2_bin())
    os.chmod(exiv2_bin(), st.st_mode | stat.S_IEXEC)
    st = os.stat(exiv2json_bin())
    os.chmod(exiv2json_bin(), st.st_mode | stat.S_IEXEC)

    # macOS workaround to avoid dynamic linking issues
    # Correct way would be to set DYLD_LIBRARY_PATH when calling exiv2,
    # but this makes it easier.
    if system().lower() == "darwin":
        lib_path = Path(exiv2_bin()).parent / ".." / "lib" / "libexiv2.27.dylib"
        lib_bin_path = Path(exiv2_bin()).parent / "libexiv2.27.dylib"
        os.symlink(lib_path, lib_bin_path)

    return exiv2_bin()


def exiv2_version_info():  # pragma: no cover
    """Get exiv2 version info"""
    try:
        r = subprocess.run([exiv2_bin(), "--version"], capture_output=True)
        vi = r.stdout.decode(sys.stdout.encoding)
        return vi
    except FileNotFoundError:
        return "exiv2 not installed"


########################################################################################
# Fpcalc                                                                               #
########################################################################################


def fpcalc_bin():  # pragma: no cover
    """Returns local path to fpcalc executable."""
    if system() == "Windows":
        return os.path.join(idk.dirs.user_data_dir, "fpcalc-{}.exe".format(FPCALC_VERSION))
    return os.path.join(idk.dirs.user_data_dir, "fpcalc-{}".format(FPCALC_VERSION))


def fpcalc_is_installed():  # pragma: no cover
    """ "Check if fpcalc is installed."""
    fp = fpcalc_bin()
    return os.path.isfile(fp) and os.access(fp, os.X_OK)


def fpcalc_download_url():
    """Return system and version dependant download url"""
    return FPCALC_URLS[system_tag()]


def fpcalc_download():  # pragma: no cover
    """Download fpcalc and return path to archive file."""
    b3 = FPCALC_CHECKSUMS.get(system_tag())
    return download_file(fpcalc_download_url(), checksum=b3)


def fpcalc_extract(archive):  # pragma: no cover
    """Extract archive with fpcalc executable."""
    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive, "r") as zip_file:
            for member in zip_file.namelist():
                filename = os.path.basename(member)
                if filename == "fpcalc.exe":
                    source = zip_file.open(member)
                    target = open(fpcalc_bin(), "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)
    elif archive.endswith("tar.gz"):
        with tarfile.open(archive, "r:gz") as tar_file:
            for member in tar_file.getmembers():
                if member.isfile() and member.name.endswith("fpcalc"):
                    source = tar_file.extractfile(member)
                    target = open(fpcalc_bin(), "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)


def fpcalc_install():  # pragma: no cover
    """Install fpcalc command line tool and return path to executable."""
    if fpcalc_is_installed():
        log.debug("Fpcalc is already installed.")
        return fpcalc_bin()
    log.critical("installing fpcalc")
    archive_path = fpcalc_download()
    fpcalc_extract(archive_path)
    st = os.stat(fpcalc_bin())
    os.chmod(fpcalc_bin(), st.st_mode | stat.S_IEXEC)
    return fpcalc_bin()


def fpcalc_version_info():  # pragma: no cover
    """Get fpcalc version"""
    try:
        r = subprocess.run([fpcalc_bin(), "-v"], stdout=subprocess.PIPE)
        return r.stdout.decode("utf-8").strip().split()[2]
    except FileNotFoundError:
        return "FPCALC not installed"


########################################################################################
# ffprobe                                                                              #
########################################################################################


def ffprobe_download_url():
    """Return system dependant download url."""
    return FFPROBE_URLS[system_tag()]


def ffprobe_bin() -> str:
    """Returns local path to ffprobe executable."""
    path = os.path.join(idk.dirs.user_data_dir, "ffprobe-{}".format(FFPROBE_VERSION))
    if system() == "Windows":
        path += ".exe"
    return path


def ffprobe_download():  # pragma: no cover
    """Download ffprobe and return path to archive file."""
    b3 = FFPROBE_CHECKSUMS.get(system_tag())
    return download_file(ffprobe_download_url(), checksum=b3)


def ffprobe_extract(archive: str):  # pragma: no cover
    """Extract ffprobe from archive."""
    fname = "ffprobe.exe" if system() == "Windows" else "ffprobe"
    with zipfile.ZipFile(archive) as zip_file:
        with zip_file.open(fname) as zf, open(ffprobe_bin(), "wb") as lf:
            shutil.copyfileobj(zf, lf)


def ffprobe_install():  # pragma: no cover
    """Install ffprobe command line tool and return path to executable."""
    if is_installed(ffprobe_bin()):
        log.debug("ffprobe is already installed")
        return ffprobe_bin()
    log.critical("installing ffprobe")
    archive_path = ffprobe_download()
    ffprobe_extract(archive_path)
    st = os.stat(ffprobe_bin())
    os.chmod(ffprobe_bin(), st.st_mode | stat.S_IEXEC)
    return ffprobe_bin()


def ffprobe_version_info():  # pragma: no cover
    """Get ffprobe version"""
    try:
        r = subprocess.run([ffprobe_bin(), "-version"], stdout=subprocess.PIPE)
        return (
            r.stdout.decode("utf-8")
            .strip()
            .splitlines()[0]
            .split()[2]
            .rstrip("-static")
            .rstrip("-tessu")
        )
    except FileNotFoundError:
        return "ffprobe not installed"


########################################################################################
# ffmpeg                                                                               #
########################################################################################


def ffmpeg_download_url():
    """Return system dependant download url."""
    return FFMPEG_URLS[system_tag()]


def ffmpeg_bin() -> str:
    """Returns local path to ffmpeg executable."""
    path = os.path.join(idk.dirs.user_data_dir, "ffmpeg-{}".format(FFMPEG_VERSION))
    if system() == "Windows":
        path += ".exe"
    return path


def ffmpeg_download():  # pragma: no cover
    """Download ffmpeg and return path to archive file."""
    b3 = FFMPEG_CHECKSUMS.get(system_tag())
    return download_file(ffmpeg_download_url(), checksum=b3)


def ffmpeg_extract(archive: str):  # pragma: no cover
    """Extract ffprobe from archive."""
    fname = "ffmpeg.exe" if system() == "Windows" else "ffmpeg"
    with zipfile.ZipFile(archive) as zip_file:
        with zip_file.open(fname) as zf, open(ffmpeg_bin(), "wb") as lf:
            shutil.copyfileobj(zf, lf)


def ffmpeg_install():  # pragma: no cover
    """Install ffmpeg command line tool and return path to executable."""
    if is_installed(ffmpeg_bin()):
        log.debug("ffmpeg is already installed")
        return ffmpeg_bin()
    log.critical("installing ffmpeg")
    archive_path = ffmpeg_download()
    ffmpeg_extract(archive_path)
    st = os.stat(ffmpeg_bin())
    os.chmod(ffmpeg_bin(), st.st_mode | stat.S_IEXEC)
    return ffmpeg_bin()


def ffmpeg_version_info():  # pragma: no cover
    """Get ffmpeg version"""
    try:
        r = subprocess.run([ffmpeg_bin(), "-version"], stdout=subprocess.PIPE)
        return (
            r.stdout.decode("utf-8")
            .strip()
            .splitlines()[0]
            .split()[2]
            .rstrip("-static")
            .rstrip("-tessu")
        )
    except FileNotFoundError:
        return "ffmpeg not installed"


########################################################################################
# Java                                                                                 #
########################################################################################


def java_bin():  # pragma: no cover
    java_path = shutil.which("java")
    if not java_path:
        java_path = java_custom_path()
    return java_path


def java_custom_path():  # pragma: no cover
    if system() == "Windows":
        java_path = os.path.join(idk.dirs.user_data_dir, "jdk-16.0.2+7-jre", "bin", "java.exe")
    else:
        java_path = os.path.join(idk.dirs.user_data_dir, "jdk-16.0.2+7-jre", "bin", "java")
    return java_path


def java_is_installed():  # pragma: no cover
    return bool(shutil.which("java")) or is_installed(java_custom_path())


def java_install():  # pragma: no cover
    if java_is_installed():
        log.debug("java already installed")
        return java_bin()
    log.critical("installing java")
    return jdk.install("16", impl="openj9", jre=True, path=idk.dirs.user_data_dir)


def java_version_info():  # pragma: no cover
    try:
        r = subprocess.run([java_bin(), "-version"], stderr=subprocess.PIPE)
        return r.stderr.decode(sys.stdout.encoding).splitlines()[0]
    except subprocess.CalledProcessError:
        return "JAVA not installed"


########################################################################################
# Apache Tika                                                                          #
########################################################################################


def tika_download_url():
    # type: () -> str
    """Return tika download url"""
    return TIKA_URL


def tika_bin():
    # type: () -> str
    """Returns path to java tika app call"""
    return os.path.join(idk.dirs.user_data_dir, f"tika-app-{TIKA_VERSION}.jar")


def tika_is_installed():  # pragma: no cover
    # type: () -> bool
    """Check if tika is installed"""
    return os.path.exists(tika_bin())


def tika_download():  # pragma: no cover
    # type: () -> str
    """Download tika-app.jar and return local path"""
    return download_file(tika_download_url(), checksum=TIKA_CHECKSUM)


def tika_install():  # pragma: no cover
    # type: () -> str
    """Install tika-app.jar if not installed yet."""
    # Ensure JAVA is installed
    java_install()

    if tika_is_installed():
        log.debug("Tika is already installed")
        return tika_bin()
    else:
        log.critical("installing tika")
        path = tika_download()
        st = os.stat(tika_bin())
        os.chmod(tika_bin(), st.st_mode | stat.S_IEXEC)
        return path


def tika_version_info():  # pragma: no cover
    # type: () -> str
    """
    Check tika-app version

    :return: Tika version info string
    :rtype: str
    """
    try:
        r = subprocess.run([java_bin(), "-jar", tika_bin(), "--version"], stdout=subprocess.PIPE)
        return r.stdout.decode(sys.stdout.encoding).strip()
    except subprocess.CalledProcessError:
        return "Tika not installed"


def download_file(url, checksum):  # pragma: no cover
    # type: (str, str) -> str
    """Download file to app directory and return path to downloaded file."""
    url_obj = urlparse(url)
    if not url_obj.scheme == "https":
        raise ValueError("Only https connections supported.")
    file_name = os.path.basename(url_obj.path)
    out_dir = idk.dirs.user_data_dir
    out_path = os.path.join(out_dir, file_name)
    if os.path.exists(out_path):
        log.debug(f"{file_name} already exists. Checking integrity")
        b3_calc = blake3(open(out_path, "rb").read()).hexdigest()
        if not checksum == b3_calc:
            log.critical(f"Integrity error for {out_path}. Redownloading")
        else:
            log.debug(f"{file_name} integrity ok - skipping redownload")
            return out_path
    log.debug(f"downloading {url} to {out_path}")
    urlretrieve(url, filename=out_path)
    log.debug(f"verifying {out_path}")
    b3_calc = blake3(open(out_path, "rb").read()).hexdigest()
    if not checksum == b3_calc:
        raise RuntimeError(f"Failed integrity check for {out_path}")
    return out_path
