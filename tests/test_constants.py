"""Pytest test suite for the constants module."""

from dataclasses import FrozenInstanceError

import pytest
from hypothesis import given, strategies

from chasten import constants


def test_filesystem_constants():
    """Confirm default values of constants."""
    assert constants.filesystem.Current_Directory == "."
    assert constants.humanreadable.Yes == "Yes"
    assert constants.humanreadable.No == "No"


@given(directory=strategies.text(), yes=strategies.text(), no=strategies.text())
@pytest.mark.hypothesis
def test_fuzz_init(directory, yes, no):
    """Use Hypothesis to confirm that initial value is set correctly."""
    fs = constants.Filesystem(directory)
    assert fs.Current_Directory == directory
    hr = constants.Humanreadable(yes, no)
    assert hr.Yes == yes
    assert hr.No == no


@given(fs=strategies.builds(constants.Filesystem), hr=strategies.builds(constants.Humanreadable))
@pytest.mark.hypothesis
def test_fuzz_immutable(fs, hr):
    """Use Hypothesis to confirm that attribute's value cannot be re-assigned."""
    with pytest.raises(FrozenInstanceError):
        fs.Current_Directory = "/new/path"
    with pytest.raises(FrozenInstanceError):
        hr.Yes = "YES"
    with pytest.raises(FrozenInstanceError):
        hr.No = "NO"


@given(dir1=strategies.text(), dir2=strategies.text())
@pytest.mark.hypothesis
def test_fuzz_distinct(dir1, dir2):
    """Use Hypothesis to confirm equality when the inputs names are the same."""
    fs1 = constants.Filesystem(dir1)
    fs2 = constants.Filesystem(dir2)
    if dir1 != dir2:
        assert fs1 != fs2
    else:
        assert fs1 == fs2


@given(directory=strategies.text())
@pytest.mark.hypothesis
def test_fuzz_dataclass_equality(directory):
    """Use Hypothesis to confirm that the same directory makes the same constant."""
    dir1 = directory
    dir2 = directory
    assert dir1 == dir2
    fs1 = constants.Filesystem(dir1)
    fs2 = constants.Filesystem(dir2)
    assert fs1 == fs2