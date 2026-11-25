import io
import sys
import tokenize

import pytest

from pycodestyle import Checker
from pycodestyle import expand_indent
from pycodestyle import get_parser
from pycodestyle import mute_string
from pycodestyle import read_config


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('    ', 4),
        ('\t', 8),
        ('       \t', 8),
        ('        \t', 16),
    ),
)
def test_expand_indent(s, expected):
    assert expand_indent(s) == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('"abc"', '"xxx"'),
        ("'''abc'''", "'''xxx'''"),
        ("r'abc'", "r'xxx'"),
    ),
)
def test_mute_string(s, expected):
    assert mute_string(s) == expected


def test_fstring_logical_line():
    src = '''\
f'hello {{ {thing} }} world'
'''
    checker = Checker(lines=src.splitlines())
    checker.tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    checker.build_tokens_line()

    if sys.version_info >= (3, 12):  # pragma: >=3.12 cover
        assert checker.logical_line == "f'xxxxxxxxx{thing}xxxxxxxxx'"
    else:  # pragma: <3.12 cover
        assert checker.logical_line == "f'xxxxxxxxxxxxxxxxxxxxxxxxx'"


def test_read_config_broken_cli_config(tmp_path):
    broken = tmp_path.joinpath('bad.cfg')
    broken.write_text('not ini\n')
    parser = get_parser()
    parser.add_option('--config')
    opts, args = parser.parse_args(['--config', str(broken)])
    with pytest.raises(SystemExit) as exc_info:
        read_config(opts, args, ['--config', str(broken)], parser)
    assert exc_info.value.code == 2


def test_read_config_broken_project_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath('setup.cfg').write_text('not ini\n')
    target = tmp_path.joinpath('t.py')
    target.touch()
    parser = get_parser()
    parser.add_option('--config')
    opts, args = parser.parse_args([str(target)])
    with pytest.raises(SystemExit) as exc_info:
        read_config(opts, args, [str(target)], parser)
    assert exc_info.value.code == 2


def test_read_config_prefix(tmp_path):
    tmp_path.joinpath('setup.cfg').write_text('[pycodestyle]\nexclude = root')

    adir = tmp_path.joinpath('aaa')
    adir.mkdir()
    adir.joinpath('setup.cfg').write_text('[pycodestyle]\nexclude = aaa')

    bdir = tmp_path.joinpath('aaabbb')
    bdir.mkdir()
    b_t = bdir.joinpath('t.py')
    b_t.touch()
    bdir.joinpath('setup.cfg').write_text('[pycodestyle]\nexclude = bbb')

    cdir = tmp_path.joinpath('aaaccc')
    cdir.mkdir()
    c_t = cdir.joinpath('t.py')
    c_t.touch()
    cdir.joinpath('setup.cfg').write_text('[pycodestyle]\nexclude = ccc')

    arglist = [str(b_t), str(c_t)]
    parser = get_parser()
    parser.add_option('--config')
    opts, args = parser.parse_args(arglist)

    # `aaa/setup.cfg` should not be read -- it is not passed on cmdline
    opts = read_config(opts, args, arglist, parser)
    assert opts.exclude == ['root']
