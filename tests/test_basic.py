"""
Note that pytest offers a `tmp_path`. 
You can reproduce locally with

```python
%load_ext autoreload
%autoreload 2
import os
import tempfile
import shutil
from pathlib import Path
tmp_path = Path(tempfile.gettempdir()) / 'pytest-retrieve-authors'
if os.path.exists(tmp_path):
    shutil.rmtree(tmp_path)
os.mkdir(tmp_path)
```
"""

import re
import shutil
import os
import pytest

from click.testing import CliRunner
from mkdocs.__main__ import build_command
from git import Repo
import git as gitpython
from contextlib import contextmanager


@contextmanager
def working_directory(path):
    """
    Temporarily change working directory.
    A context manager which changes the working directory to the given
    path, and then changes it back to its previous value on exit.
    Usage:
    ```python
    # Do something in original directory
    with working_directory('/my/new/path'):
        # Do something in new directory
    # Back to old directory
    ```
    """
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def build_docs_setup(mkdocs_path, output_path):
    runner = CliRunner()
    return runner.invoke(
        build_command, ["--config-file", mkdocs_path, "--site-dir", str(output_path)]
    )

@pytest.mark.parametrize(
    "mkdocs_file",
    ["mkdocs.yml", "mkdocs_w_macros.yml", "mkdocs_w_macros2.yml", "mkdocs_complete_material.yml"],
)
def test_basic_working(tmp_path, mkdocs_file):
    """
    combination with mkdocs-macros-plugin lead to error.
    See https://github.com/timvink/mkdocs-git-authors-plugin/issues/60    
    """
    result = build_docs_setup("tests/basic_setup/mkdocs.yml", tmp_path)
    assert result.exit_code == 0, (
        "'mkdocs build' command failed. Error: %s" % result.stdout
    )

    index_file = tmp_path / "index.html"
    assert index_file.exists(), "%s does not exist" % index_file

    contents = index_file.read_text()
    assert re.search("<span class='git-page-authors", contents)
    assert re.search("<li><a href='mailto:vinktim@gmail.com'>Tim Vink</a></li>", contents)



def test_exclude_working(tmp_path):

    result = build_docs_setup("tests/basic_setup/mkdocs_exclude.yml", tmp_path)
    assert result.exit_code == 0, (
        "'mkdocs build' command failed. Error: %s" % result.stdout
    )

    page_file = tmp_path / "page_with_tag/index.html"
    assert page_file.exists(), "%s does not exist" % page_file

    contents = page_file.read_text()
    assert not re.search("<span class='git-page-authors", contents)



def test_exclude_working_with_genfiles(tmp_path):
    """
    A warning for uncommited files should not show up
    when those uncommited files are excluded.
    """
    
    testproject_path = tmp_path / "testproject_genfiles"

    shutil.copytree(
        "tests/basic_setup/docs", str(testproject_path / "docs")
    )
    shutil.copyfile(
        "tests/basic_setup/mkdocs_genfiles.yml",
        str(testproject_path / "mkdocs.yml"),
    )

    with working_directory(str(testproject_path)):
        # setup git history
        repo = Repo.init(testproject_path)
        assert not repo.bare
        repo.git.add(all=True)
        repo.index.commit("first commit")

        # generate a file manually, do not commit
        with open(testproject_path / "docs" / "manually_created.md", "w") as f:
            f.write("Hello, world!")

        # generate another file manually, do not commit
        another_path = testproject_path / "docs" / "somefolder"
        os.mkdir(another_path)
        with open(another_path / "manually_created_infolder.md", "w") as f:
            f.write("Hello, world!")

        # mkdocs build
        # mkdocs.yml has exclusions for the created files
        result = build_docs_setup(
            str(testproject_path / "mkdocs.yml"), str(testproject_path / "site")
        )
        assert result.exit_code == 0, (
                "'mkdocs build' command failed. Error: %s" % result.stdout
        )

        # files generated ourselves right before build but not committed, should not generate warnings
        assert "manually_created.md has not been committed yet." not in result.stdout
        assert "manually_created_infolder.md has not been committed yet." not in result.stdout



def test_enabled_working(tmp_path):

    result = build_docs_setup("tests/basic_setup/mkdocs_complete_material_disabled.yml", tmp_path)
    assert result.exit_code == 0, (
        "'mkdocs build' command failed. Error: %s" % result.stdout
    )

    page_file = tmp_path / "page_with_tag/index.html"
    assert page_file.exists(), "%s does not exist" % page_file

    contents = page_file.read_text()
    assert not re.search("<span class='git-page-authors", contents)



def test_project_with_no_commits(tmp_path):
    """
    Structure:
    
    tmp_path/testproject
    website/
        ├── docs/
        └── mkdocs.yml"""
    testproject_path = tmp_path / "testproject"

    shutil.copytree(
        "tests/basic_setup/docs", str(testproject_path / "website" / "docs")
    )
    shutil.copyfile(
        "tests/basic_setup/mkdocs_w_contribution.yml",
        str(testproject_path / "website" / "mkdocs.yml"),
    )

    with working_directory(str(testproject_path)):
        # run 'git init'
        gitpython.Repo.init(testproject_path, bare=False)

        result = build_docs_setup(
            str(testproject_path / "website/mkdocs.yml"), str(testproject_path / "site")
        )
        assert result.exit_code == 0, (
            "'mkdocs build' command failed. Error: %s" % result.stdout
        )




def test_building_empty_site(tmp_path):
    """
    Structure:
    
    ```
    tmp_path/testproject
    website/
        ├── docs/
        └── mkdocs.yml
    ````
    """
    testproject_path = tmp_path / "testproject"

    shutil.copytree(
        "tests/basic_setup/empty_site", str(testproject_path / "website" / "docs")
    )
    shutil.copyfile(
        "tests/basic_setup/mkdocs_w_contribution.yml",
        str(testproject_path / "website" / "mkdocs.yml"),
    )

    with working_directory(str(testproject_path)):
        # run 'git init'
        gitpython.Repo.init(testproject_path, bare=False)

        result = build_docs_setup(
            str(testproject_path / "website/mkdocs.yml"), str(testproject_path / "site")
        )
        assert result.exit_code == 0, (
            "'mkdocs build' command failed. Error: %s" % result.stdout
        )



def test_fallback(tmp_path):
    """
    Structure:
    
    ```
    tmp_path/testproject
    website/
        ├── docs/
        └── mkdocs.yml
    ````
    """
    testproject_path = tmp_path / "testproject"

    shutil.copytree(
        "tests/basic_setup/docs", str(testproject_path / "website" / "docs")
    )
    shutil.copyfile(
        "tests/basic_setup/mkdocs_fallback.yml",
        str(testproject_path / "website" / "mkdocs.yml"),
    )

    with working_directory(str(testproject_path)):

        result = build_docs_setup(
            str(testproject_path / "website/mkdocs.yml"), str(testproject_path / "site")
        )
        # import pdb; pdb.set_trace()
        assert result.exit_code == 0, (
            "'mkdocs build' command failed. Error: %s" % result.stdout
        )
