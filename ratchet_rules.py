import copy
import re
from typing import Callable
from typing import Tuple

from research.ratchets.ratchet_utils import FullFileRatchetTest
from research.ratchets.ratchet_utils import RatchetTest
from research.ratchets.ratchet_utils import RegexBasedRatchetTest
from research.ratchets.ratchet_utils import TwoPassRatchetTest
from research.ratchets.ratchet_utils import make_regex_part_matching_import_from_failure

path_exclude_check = RegexBasedRatchetTest(
    # This isn't part of the list of ratchets because it should never have any violations. It checks for a string that
    # shouldn't appear in our codebase naturally, but that has been intentionally added to some files that we exclude.
    # This way we can make sure that our exclude rules are working properly.
    name="path_exclude_checks",
    regex=re.compile(r"a_long_string_that_shouldnt_appear_anywhere_naturally"),
    match_examples=[
        "a_long_string_that_shouldnt_appear_anywhere_naturally",
        "def a_long_string_that_shouldnt_appear_anywhere_naturally",
    ],
    non_match_examples=[],
)


ratchet_test_builders: Tuple[Callable[[], RatchetTest], ...] = tuple(
    map(
        # a function (for mapping) that returns a function that creates a fresh, isolated instance of this ratchet test.
        # done to avoid these tests being as stateful - We don't want to accidentally share failures across runs if we
        # run a test twice or similar.
        lambda x: lambda: copy.deepcopy(x),
        [
            RegexBasedRatchetTest(
                name="pytorch_lightning",
                regex=re.compile(r"import pytorch_lightning|from pytorch_lightning"),
                match_examples=[
                    "from pytorch_lightning import LightningModule",
                    "import pytorch_lightning as pl",
                ],
                non_match_examples=["from this_package import the_thing", "import super_lightning as sl"],
            ),
            RegexBasedRatchetTest(
                name="crafty_deprecated_hammer_task",
                regex=re.compile(r"from imbue.agents.primitives.current_hammer"),
                match_examples=[
                    "from imbue.agents.primitives.current_hammer import create_hammer_task",
                    "from imbue.agents.primitives.current_hammer import current_task_id",
                ],
                non_match_examples=["from imbue_core.clean_tasks", "from imbue.agents.primitives.blah"],
                include_file_regex=re.compile(r"crafty/crafty/.*\.py"),
            ),
            RegexBasedRatchetTest(
                name="unsafe_async_cancel",
                regex=re.compile(r"\.cancel\(\)"),
                match_examples=[
                    "task.cancel()",
                    "some_agent.cancel()",
                ],
                non_match_examples=["something.cancel_everything()", "ref = thing.cancel"],
            ),
            RegexBasedRatchetTest(
                name="eval",
                # not sure this is bulletproof.
                # Trying to filter for just calling a function named `eval`.
                # basically: `eval(` is only bad if preceeded by a space or opening parenthesis or newline,
                # but not if preceeded by `def ` or .
                regex=re.compile(r"(?<!def)(^|[ (])eval\("),
                match_examples=[
                    "output = eval(stuff)",
                    "print(eval(more asdf))",
                    'eval("things")',
                    "things = eval(stuff, globals=globals)",
                ],
                non_match_examples=["def eval(asdf):", '"don\'t use eval in code!"', "my_custom_class.eval(data)"],
            ),
            RegexBasedRatchetTest(
                name="relative_imports",
                regex=re.compile(r"^from \.\.?([\w.]+)? import [\w]+( as \w+)?\Z"),
                match_examples=[
                    "from . import thing",
                    "from .. import thing",
                    "from .thing import thing",
                    "from ..thing import thing",
                    "from .thing.thing import thing",
                ],
                non_match_examples=[
                    "from thing import thing",
                ],
            ),
            RegexBasedRatchetTest(
                name="NamedTuple",
                # Not gonna get fancy here, really no valid reason we'd need this string anywhere
                regex=re.compile(r"NamedTuple"),
                match_examples=[
                    "from typing import NamedTuple",
                    "class RolloutBufferSamples(NamedTuple):",
                ],
            ),
            RegexBasedRatchetTest(
                name="logger.warning",
                regex=re.compile(r"logger\.warning"),
                match_examples=["logger.warning('Something Broke!')", "   logger.warning('duck! %i' % (count))"],
                non_match_examples=["logger.info('something boring')", "logger.error('this should be impossible!')"],
            ),
            RegexBasedRatchetTest(
                name="attrs",
                # Valid flags in alphabetical order except auto_exc which usually indicates a structured error
                regex=re.compile(
                    r"@attr.s\((?!((auto_exc=True, )?auto_attribs=True(, frozen=True)?(, kw_only=True)?(, repr=False)?)\))"
                ),
                match_examples=[
                    "@attr.s()"
                    "@attr.s(pretty, much, any, arguments)"
                    "   @attr.s(pretty, much, any, arguments)"
                    "   @attr.s(key=word, arg=uments)"
                    "@attr.s(auto_attribs=True, hash=True, collect_by_mro=True)",
                ],
                non_match_examples=[
                    "@attr.s(auto_attribs=True, frozen=True)",
                    "@attr.s(auto_attribs=True)",
                    "@attr.s(auto_exc=True, auto_attribs=True)",
                    "@attr.s(auto_exc=True, auto_attribs=True, repr=False)",
                ],
            ),
            # TODO: is this a ratchet we want? it wasn't on the list given to me
            # RatchetTest(
            #     name="isinstance",
            #     # Not gonna get fancy here, really no valid reason we'd need this string anywhere
            #     regex=re.compile(r"isinstance\("),
            # ),
            RegexBasedRatchetTest(
                name="args_kwargs",
                regex=re.compile(r"(def \w+\(.*\*args(?!: P\.args))|(def \w+\(.*\*\*kwargs(?!: P\.kwargs))"),
                match_examples=[
                    "    def params(cls, **kwargs) -> SupervisedModelParams:",
                    "    def render(self, *args, **kwargs):",
                    "    def extend(self, *args, **kwargs) -> None:",
                    "    def not_actually_paramspec(self, *args: Paargs) -> None:",
                    "def use(*args: Callable[..., Any]) -> Any:",
                ],
                non_match_examples=[
                    "def using_param_spec_for_metafunction(*args: P.args)",
                    "def using_param_spec_for_metafunction(**kwargs: P.kwargs)",
                    "return cls(**kwargs)",
                    "        yield super().reconfigService(generators=generators, **kwargs)",
                    "            numba_assign(*args)",
                ],
            ),
            RegexBasedRatchetTest(
                name="import_underscore",
                regex=re.compile(r"^(from [\w.]+ )?import __?\w+"),
                exclude_test_files=True,
                match_examples=[
                    "import _thing",
                    "import __thing",
                    "from thing import _thing",
                    "from thing import __thing",
                    "from thing.thing import _thing",
                    "from thing.thing import __thing",
                ],
                non_match_examples=[
                    "import stuff",
                    "from stuff import thing",
                ],
            ),
            FullFileRatchetTest(
                name="inline_functions",
                # We can tell if a function is inline because it will be indented
                # and not have `cls` or `self` as the first argument.
                # This has to be a full file ratchet test b/c the first function argument can have a newline before it.
                regex=re.compile(
                    r"(?<!@staticmethod\n)(?<!@abstractmethod\n)^[ \t]+def\s+\w+\((?!\s*cls|\s*self)",
                    flags=re.MULTILINE,
                ),
                match_examples=[
                    "    def inline()",
                    "  def indented_not_far()",
                    "  def indented_not_far(with_arguments)",
                ],
                non_match_examples=[
                    "    def with_slf(self)",
                    "    def with_class(cls)",
                    "    def with_many_args(cls, asdf, test: str)",
                    "    def with_many_args(\n     cls, asdf, test: str)",
                    "    def with_many_args(\ncls, asdf, test: str)",
                    "    def with_many_args(\n     self, asdf, test: str)",
                    "    def with_many_args(\nself, asdf, test: str)",
                    "@staticmethod\n    def static_method()",
                    "@staticmethod\n    @abstractmethod\n    def abstract_static_method()",
                    "    @staticmethod\n    @abstractmethod\n    def abstract_static_method_with_indentation()",
                ],
            ),
            # TODO: maybe this should be a two-line test that excludes TYPE_CHECKING conditional imports,
            #  or even TYPE_CHECKING for only external imports, however we would do that.
            RegexBasedRatchetTest(
                name="inline_imports",
                regex=re.compile(r"(^\s+import [\w.]+( as \w+)?\Z)|(^\s+from [\w.]+ import)"),
                match_examples=[
                    "    import stuff",
                    "       import stuff",
                    "         import stuff",
                    "    import stuff.morestuff",
                    "    import stuff as otherstuff",
                    "    import stuff.morestuff as otherstuff",
                    "    from stuff import thing",
                    "    from stuff import thing as otherthing",
                    "    from stuff.thing import thing",
                    "    from stuff.thing import thing as otherthing",
                ],
                non_match_examples=[
                    "import stuff",
                    "from stuff import thing",
                    "        important_points = add_detail_near_items(self.map, [item], item.get_offset())",
                    "    import along with all of your other imports at the top of your notebook",
                    "       importlib.reload(module)",
                    "# from avalon.agent.common.storage import StorageMode",
                    "# import StorageMode",
                ],
            ),
            RegexBasedRatchetTest(
                name="import_quarantine",
                regex=re.compile(r"\s*(from|import)\s+.*quarantine"),
                match_examples=[
                    "import research.quarantine.someone",
                    "import quarantine.someone",
                    "from research.quarantine.someone",
                    "from quarantine.someone import something",
                ],
                non_match_examples=[
                    "_quarantine",
                    "quarantine_",
                ],
            ),
            RegexBasedRatchetTest(
                name="quarantine_paths",
                # Intended to prevent commands from calling files in quarantine
                regex=re.compile(r"quarantine/"),
                match_examples=[
                    "quarantine/someone/",
                    "quarantine/someone/simple_experiment_script.py train",
                ],
                non_match_examples=[
                    "quarantine",
                ],
            ),
            RegexBasedRatchetTest(
                name="walrus_operator",
                # Prevent usage of the walrus operator. Too easy to miss assignments and cause bugs.
                regex=re.compile(r" := "),
                match_examples=[
                    "x := 4/",
                ],
                non_match_examples=[
                    "y = 4",
                ],
            ),
            RegexBasedRatchetTest(
                name="non_sys_exit",
                # Prevent usage of exit builtin. Too easy to accidentally use it instead of sys.exit.
                regex=re.compile(r"(?<!sys\.)\bexit\(\d+\)"),
                match_examples=[
                    "exit(0)",
                    "exit(1)",
                    "exit(255)",
                ],
                non_match_examples=[
                    "sys.exit(0)",
                    "sys.exit(1)",
                    "sys.exit(255)",
                ],
            ),
            RegexBasedRatchetTest(
                name="ssh_subprocess",
                # Prevent usage of subprocess with ssh commands.
                # We have nice common abstractions for this in the codebase.
                regex=re.compile(r"subprocess\.(Popen|run|call|check_call|check_output)\([^)]*?ssh[^)]*?\)"),
                match_examples=[
                    "subprocess.Popen(['ssh', 'user@host', 'command'], stdout=subprocess.PIPE)",
                    "subprocess.check_call('ssh', shell=True)",
                    "subprocess.run(['ssh', 'user@host', 'command'], stdout=subprocess.PIPE)",
                    "subprocess.call(['ssh', 'user@host', 'command'], stdout=subprocess.PIPE)",
                    "subprocess.Popen(['ssh', 'user@host', 'command'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)",
                    "subprocess.check_call(['ssh', 'user@host', 'command'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)",
                    "subprocess.call(['ssh', 'user@host', 'command'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)",
                    "subprocess.run(['ssh', 'user@host', 'command'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)",
                ],
                non_match_examples=[
                    "ssh_connection.run_command('command')",
                    "subprocess.Popen(['ls', '-l'], stdout=subprocess.PIPE)",
                    "subprocess.check_call(['ls', '-l'], stdout=subprocess.PIPE)",
                    "subprocess.call(['ls', '-l'], stdout=subprocess.PIPE)",
                ],
            ),
            RegexBasedRatchetTest(
                name="use_pathlib_over_os.path.join",
                regex=re.compile(r"os\.path\.join"),
                match_examples=[
                    "os.path.join('some_file', 'another_file')",
                    "import os.path.join as my_special_function",
                ],
                non_match_examples=["import os.path", "path.join('some file with spaces', 'a dog')"],
            ),
            FullFileRatchetTest(
                name="implicit_string_concat",
                # Prevent implicitly concatenated multiline strings.
                # The regex is not 100% correct but without a full parser, we probably can't do much better.
                # It should cover the vast majority of cases.
                regex=re.compile(r'^[^"\n]*"[^"]+"\s*f?"[^"]+', flags=re.MULTILINE),
                match_examples=[
                    'help_text="This is some long"\n    "help text"',
                    'help_text=f"This is some {var} long"\n    f"help {var} text"',
                    '    paragraph = (\n        "First line of a paragraph"\n        "Second line of a paragraph"\n    )',
                    'text="one " "two"',
                    'text=f"one " f"two"',
                ],
                non_match_examples=[
                    '    help_text = "This is some long help text"',
                    '    paragraph = "\\n".join(["First line of a paragraph", "Second line of a paragraph"])',
                    '    paragraph = "\\n".join(["First line of a paragraph",\n      "Second line of a paragraph"])',
                    'def fn():\n    """\n    Docstring\n    """\n',
                    'val = ""',
                    "val = \"\n\n''\n\n\"",
                    "val = f\"\n\nf''\n\n\"",
                    'def fn():\n    """ Docstring """',
                    'message = "that\'s lame"',
                    '"""\nmessage = "that\'s lame"\n"""',
                    'message = f"that\'s lame"',
                ],
            ),
            FullFileRatchetTest(
                name="non_build_classmethods",
                # We try not to use the classmethod decorator except as a constructor, which should start with "build" or "from".
                # "load" is allowed too, to make something nice for save vs load
                regex=re.compile(
                    r"(?<=(@classmethod\n    ))(async )?def (?!(from_|build|load|_build|get_config))",
                    flags=re.MULTILINE,
                ),
                match_examples=[
                    "@classmethod\n    def something",
                ],
                non_match_examples=[
                    "@classmethod\n    def build",
                    "@classmethod\n    def build_from",
                    "@classmethod\n    def from_something",
                    "@classmethod\n    def load",
                ],
            ),
            FullFileRatchetTest(
                name="non_private_staticmethods",
                # We try not to use the staticmethod decorator except for methods that are private to that class, ie, just for its implementation
                regex=re.compile(r"(?<=(@staticmethod\n    ))def (?!(_))", flags=re.MULTILINE),
                match_examples=[
                    "@staticmethod\n    def something",
                ],
                non_match_examples=[
                    "@staticmethod\n    def _something",
                    "@staticmethod\n    def _blah",
                ],
            ),
            FullFileRatchetTest(
                name="mutable_attr_in_frozen_dataclass",
                # frozen=True implies that you should NOT be modifying the data!
                # Thus we check to ensure that there are no Dict, List, or Set elements in frozen classes
                regex=re.compile(
                    r"@attr.s\(auto_attribs=True, frozen=True.*\)\nclass .+?\n((    [^:\n]+?: [^\n]+?\n)|(    #.*?\n)|(\n)|(    \"\"\".*?\"\"\"\n)|(    \".*?\"\n))*(    [^( :\n]+?: ((Dict)|(Set)|(List)))",
                    flags=re.MULTILINE,
                ),
                match_examples=[
                    "@attr.s(auto_attribs=True, frozen=True)\nclass blah:\n    a: Dict[str, int]",
                    "@attr.s(auto_attribs=True, frozen=True)\nclass blah:\n    a: Set[str]",
                    "@attr.s(auto_attribs=True, frozen=True)\nclass blah:\n    a: List[str]",
                    '@attr.s(auto_attribs=True, frozen=True)\nclass blah:\n    "some docstring"\n    a: Dict[str, int]',
                    "@attr.s(auto_attribs=True, frozen=True)\nclass blah:\n    a: str\n    b: Dict[str, int]",
                ],
                non_match_examples=[
                    "@attr.s(auto_attribs=True, frozen=True)\nclass blah:\n    a: str\n    b: Mapping[str, int]",
                    "@attr.s(auto_attribs=True, frozen=True)\nclass blah:\n    a: str\nb: Dict[str, int] = {}",
                    "@attr.s(auto_attribs=True, frozen=True)\nclass blah:\n    a: str\n    def thing(x: Dict[str, int]) -> None:",
                    "@attr.s(auto_attribs=True, frozen=True)\nclass blah:\n    def _get_text(self, row: pd.Series) -> str:\n        sections: List[str] = []",
                ],
            ),
            RegexBasedRatchetTest(
                name="disallow_builtin_hash_function",
                regex=re.compile(r"[^a-zA-Z_]hash\("),
                match_examples=[
                    "text_hash = hash(text)",
                    "return tensor_hash(a)*hash(str_b)",
                ],
                non_match_examples=[
                    "return tensor_hash(a)",
                    "please use this function to compute the hash of a tensor",
                    "@attr.s(auto+attribs=True,hash=True)",
                    "hashlib.md5(data).hexdigest()",
                ],
            ),
            TwoPassRatchetTest(
                name="dont_import_from_modules_that_use_inline_install",
                first_pass=RegexBasedRatchetTest(
                    name="find_inline_install_imports",
                    regex=re.compile(
                        r"(from computronium.common.dependency_utils import inline_install)|(dependency_utils.inline_install)"
                    ),
                    match_examples=[
                        "from computronium.common.dependency_utils import inline_install",
                        'dependency_utils.inline_install("pypi-simple==1.2.0")',
                    ],
                    non_match_examples=[
                        "from computronium.common.parallel_utils import parallel_executor",
                        "from benign_utils import inline_install",
                    ],
                ),
                # In the second pass, detect importing from modules that import inline_install.
                first_pass_failure_to_second_pass_regex_part=make_regex_part_matching_import_from_failure,
                # tests
                first_pass_failure_filepath_for_testing="first_pass/find_inline_install_imports.py",
                match_examples=[
                    "import first_pass.find_inline_install_imports",
                    "from first_pass.find_inline_install_imports import foo",
                    "from first_pass import find_inline_install_imports",
                ],
                non_match_examples=[
                    "from computronium.common.parallel_utils import parallel_executor",
                    "from benign_utils import inline_install",
                ],
            ),
            RegexBasedRatchetTest(
                name="make_composite_seed",
                regex=re.compile(r"[^a-zA-Z_]make_composite_seed\("),
                match_examples=[
                    "seed = make_composite_seed(seed, worker_id)",
                    "return make_composite_seed(seed, idx)",
                ],
                non_match_examples=[
                    "return quarantined_make_composite_seed(seed, idx)",
                    "do not use make_composite_seed, instead use the CompositeSeed class.",
                ],
            ),
            RegexBasedRatchetTest(
                name="default_rng",
                regex=re.compile(r"(np|numpy)\.random\.default_rng\("),
                match_examples=[
                    "rand = np.random.default_rng(seed)",
                    "return numpy.random.default_rng(seed)",
                ],
                non_match_examples=[
                    "return default_rng(seed)",
                    "rand = numpy.random()",
                ],
            ),
            RegexBasedRatchetTest(
                name="asyncio.run",
                regex=re.compile(r"asyncio\.run\("),
                match_examples=[
                    "asyncio.run(main())",
                    "asyncio.run(",
                ],
                non_match_examples=[
                    "wrapped_asyncio_run(main())",
                ],
            ),
            RegexBasedRatchetTest(
                name="logger.exception",
                regex=re.compile(r"logger\.exception\("),
                match_examples=[
                    "logger.exception(e)",
                    "logger.exception(",
                ],
                non_match_examples=[
                    "log_exception(e)",
                ],
            ),
            # We don't actually need a no local type_checking imports rule - its already covered by the no inline imports rule
            # if implemented, could look something like the following
            # no_typecheck_import_names = ["science", "computronium", "avalon"] # maybe get these programmatically?
            # no_typecheck_import_matcher = "|".join(no_typecheck_import_names)
            # RegexBasedRatchetTest(
            #     name="No local type_checking imports",
            #     # example failure in the wild: https://gitlab.com/generally-intelligent/generally_intelligent/-/blob/main/standalone/avalon/avalon/datagen/godot_env/godot_env.py#L48
            #     regex=re.compile("(^\\s+import (%s)[\\w.]+( as \\w+)?)|(^\\s+from (%s)[\\w.]+ import)" % (no_typecheck_import_matcher, no_typecheck_import_matcher)),
            #     # preceded by an if TYPE_CHECKING: line
            #
            #     # last_line_regex=re.compile(r"(if TYPE_CHECKING:)"),
            #     match_examples=[
            #         "\n    from avalon.datagen.godot_env.replay import GodotEnvReplay"
            #     ],
            #     non_match_examples=[
            #         "\n    from torch import something"
            #         "if TYPE_CHECKING:\n    from torch import something"
            #     ]
            # ),
            # TODO: We'd like to have a test to disallow inline comments, but with hashes being able to appear in strings and
            #  multiline strings existing, that's not possible with a regex. Investigate using libcst to strip strings?
            #  or build it in a future tool with AST powers.
        ],
    )
)
