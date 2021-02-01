import idaes.solvers
import pytest
import os
import idaes.logger as idaeslog

_log = idaeslog.getLogger(__name__)

def _del_data_file(path):
    path = os.path.join(idaes.data_directory, path)
    try:
        os.remove(path)
    except OSError:
        pass

@pytest.mark.unit
def test_dl_bin():
    _del_data_file(os.path.join(idaes.testing_directory, "version_lib.txt"))
    _del_data_file(os.path.join(idaes.testing_directory, "version_solvers.txt"))
    ll = _log.getEffectiveLevel() # verbose will set level to DEBUG
    idaes.solvers.download_binaries(
        release=idaes.config.default_binary_release,
        verbose=True,
        to_path="testing")
    _log.setLevel(ll) # set logger level bakc to whatever it was
    assert os.path.exists(os.path.join(idaes.testing_directory, "version_lib.txt"))
    assert os.path.exists(os.path.join(idaes.testing_directory, "version_solvers.txt"))

@pytest.mark.unit
def test_dl_bin_unknown():
    _del_data_file(os.path.join(idaes.testing_directory, "version_lib.txt"))
    _del_data_file(os.path.join(idaes.testing_directory, "version_solvers.txt"))
    with pytest.raises(Exception):
        idaes.solvers.download_binaries(
            platform="unknown platform",
            release=idaes.config.default_binary_release,
            to_path="testing")
