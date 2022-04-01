from typing import Union, Dict

from arclet.alconna.builtin.construct import AlconnaString, AlconnaFormat
from arclet.alconna.types import AnyStr, AnyDigit, ArgPattern, PatternToken
from arclet.alconna import Alconna, Args, Option
from arclet.alconna import commandManager
from devtools import debug

print(commandManager)

ping = "Test" @ AlconnaString("ping <url:url>")
ping1 = AlconnaString("ping <url:url>")

Alconna.setCustomTypes(digit=int)
alc = AlconnaFormat(
    "lp user {target} perm set {perm} {default}",
    {"target": AnyStr, "perm": AnyStr, "default": Args["de":bool:True]},
)
alcc = AlconnaFormat(
    "lp1 user {target}",
    {"target": str}
)

alcf = AlconnaFormat("music {artist} {title:str} singer {name:str}")
print(alcf.parse("music --help"))
debug(alc)
alc.exception_in_time = False
debug(alc.parse("lp user AAA perm set admin"))

aaa = AlconnaFormat("a {num}", {"num": AnyDigit})
r = aaa.parse("a 1")
print(aaa)
print(r)
print('\n')


def test(wild, text: str, num: int, boolean: bool = False):
    print('wild:', wild)
    print('text:', text)
    print('num:', num)
    print('boolean:', boolean)


alc1 = Alconna("test5", action=test)

print(alc1)

test_type = ArgPattern(r"(\[.*?])", token=PatternToken.REGEX_TRANSFORM, originType=list)

alc2 = Alconna("test", helpText="测试help直接发送") + Option("foo", Args["bar":str, "bar1":int:12345, "bar2":test_type])
print(alc2.parse("test --help"))

dic = alc1.toDict()

debug(dic)

dic['command'] = 'test_type_1'

alc3 = Alconna.fromDict(dic)
print(alc3)
print(alc3.getHelp())
print(alc3.parse("test_type_1 abcd 'testing a text' 2"))

alc4 = Alconna(
    command="test_multi",
    options=[
        Option("--foo", Args["*tags":str:1, "str1":str]),
        Option("--bar", Args["num": int]),
    ]
)

print(alc4.parse("test_multi --foo ab --bar 1"))
alc4.shortcut("st", "test_multi --foo ab --bar 1")
result = alc4.parse("st")
print(result)
print(result.getFirstArg("foo"))

alc5 = Alconna("test_anti", "!path:int")
print(alc5.parse("test_anti a"))

alc6 = Alconna("test_union", mainArgs=Args.path[Union[int, float, 'abc']])
print(alc6.parse("test_union abc"))

alc7 = Alconna("test_list", mainArgs=Args.seq[list])
print(alc7)
print(alc7.parse("test_list \"['1', '2', '3']\""))

alc8 = Alconna("test_dict", mainArgs=Args.map[Dict[str, int]])
print(alc8)
print(alc8.parse("test_dict \"{'a':1, 'b':2}\""))

alc9 = Alconna("test_str", mainArgs="@foo:str, bar:list, ?baz:int")
print(alc9)
print(alc9.parse("test_str foo=a \"[1]\""))

alc10 = Alconna("test_bool", mainArgs="?_foo:str")
print(alc10.parse(["test_bool", 1]))
print(alc10.getHelp())

alc11 = Alconna("test_header", headers=[(1234, "abc")])
print("alc11:", alc11.parse([1234, "abctest_header"]))

alc12 = Alconna("test_str1", Args["abcd", "1234"])
print("alc12:", alc12.parse("test_str1 abcd 1234"))

alc13 = Alconna("image", Args["@?--width":int:1920, "@?--height":int:1080])
print("alc13:", alc13.parse("image --height=720"))