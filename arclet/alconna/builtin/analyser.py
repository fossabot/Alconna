from typing import Union, Optional, Dict, Any
import traceback

from arclet.alconna.component import Option, Subcommand
from arclet.alconna.arpamar import Arpamar
from arclet.alconna.types import (
    DataCollection, MultiArg, ArgPattern, AntiArg, UnionArg, ObjectPattern, SequenceArg, MappingArg
)
from arclet.alconna.visitor import AlconnaNodeVisitor
from arclet.alconna.analysis.analyser import Analyser
from arclet.alconna.manager import command_manager
from arclet.alconna.analysis.arg_handlers import (
    multi_arg_handler, common_arg_handler, anti_arg_handler, union_arg_handler
)
from arclet.alconna.analysis.parts import analyse_args, analyse_option, analyse_subcommand, analyse_header
from arclet.alconna.exceptions import ParamsUnmatched, ArgumentMissing, NullTextMessage, UnexpectedElement
from arclet.alconna.util import split
from .actions import help_send


class DisorderCommandAnalyser(Analyser):
    """
    无序的分析器

    """

    chain_texts = ["Plain", "Text"]
    elements_blacklist = ["Source", "File", "Quote"]

    def add_param(self, opt: Union[Option, Subcommand]):
        if isinstance(opt, Subcommand):
            for sub_opts in opt.options:
                opt.sub_params.setdefault(sub_opts.name, sub_opts)
        self.params[opt.name] = opt

    def handle_message(self, data: Union[str, DataCollection]) -> Optional[Arpamar]:
        """命令分析功能, 传入字符串或消息链, 应当在失败时返回fail的arpamar"""
        if isinstance(data, str):
            self.is_str = True
            res = split(data.lstrip(), self.separator)
            if not res:
                if self.is_raise_exception:
                    raise NullTextMessage("传入了空的字符串")
                return self.create_arpamar(fail=True, exception=NullTextMessage("传入了空的字符串"))
            self.raw_data = {0: res}
            self.ndata = 1
        else:
            separate = self.separator
            i, __t, exc = 0, False, None
            raw_data: Dict[int, Any] = {}
            for unit in data:  # type: ignore
                if text := getattr(unit, 'text', None):
                    res = split(text.lstrip(' '), separate)
                    if not res:
                        continue
                    raw_data[i] = res
                    __t = True
                elif unit.__class__.__name__ not in self.elements_blacklist:
                    raw_data[i] = unit
                elif isinstance(unit, str):
                    res = split(unit.lstrip(' '), separate)
                    if not res:
                        continue
                    raw_data[i] = res
                    __t = True
                else:
                    if self.is_raise_exception:
                        exc = UnexpectedElement(f"{unit.type}({unit})")
                    continue
                i += 1
            if __t is False:
                if self.is_raise_exception:
                    raise NullTextMessage("传入了一个无法获取文本的消息链")
                return self.create_arpamar(fail=True, exception=NullTextMessage("传入了一个无法获取文本的消息链"))
            if exc:
                if self.is_raise_exception:
                    raise exc
                return self.create_arpamar(fail=True, exception=exc)
            self.raw_data = raw_data
            self.ndata = i

    def analyse(self, message: Union[str, DataCollection, None] = None) -> Arpamar:
        if command_manager.is_disable(self.alconna):
            return self.create_arpamar(fail=True)
        if self.ndata == 0:
            if not message:
                raise ValueError('No data to analyse')
            if r := self.handle_message(message):
                return r
        self.header = analyse_header(self)
        if self.header is False:
            self.current_index = 0
            self.content_index = 0
            try:
                _, cmd, reserve = command_manager.find_shortcut(
                    self.alconna, self.next_data(self.alconna.separator, pop=False)[0]
                )
                if reserve:
                    data = self.recover_raw_data()
                    data[0] = cmd
                    self.reset()
                    return self.analyse(data)  # type: ignore
                self.reset()
                return self.analyse(cmd)
            except ValueError:
                return self.create_arpamar(fail=True)

        for _ in self.part_len:
            _text, _str = self.next_data(self.separator, pop=False)
            _param = self.params.get(_text, Ellipsis) if _str else None
            if _param is Ellipsis and _text != "":
                for p in self.params:
                    if _text.startswith(getattr(self.params[p], 'alias', p)):
                        _param = self.params[p]
                        break
            try:
                if not _param:
                    if not self.main_args:
                        self.main_args = analyse_args(
                            self, self.self_args, self.separator, self.alconna.nargs, self.alconna.action
                        )
                elif isinstance(_param, Option):
                    if _param.name == "--help":
                        def _get_help():
                            visitor = AlconnaNodeVisitor(self.alconna)
                            return visitor.format_node(
                                self.alconna.formatter,
                                visitor.require(self.recover_raw_data())
                            )

                        _param.action = help_send(
                            self.alconna.name, _get_help
                        )
                        analyse_option(self, _param)
                        return self.create_arpamar(fail=True)
                    opt_n, opt_v = analyse_option(self, _param)
                    if not self.options.get(opt_n, None):
                        self.options[opt_n] = opt_v
                    elif isinstance(self.options[opt_n], dict):
                        self.options[opt_n] = [self.options[opt_n], opt_v]
                    else:
                        self.options[opt_n].append(opt_v)

                elif isinstance(_param, Subcommand):
                    sub_n, sub_v = analyse_subcommand(self, _param)
                    self.subcommands[sub_n] = sub_v

            except (ParamsUnmatched, ArgumentMissing):
                if self.is_raise_exception:
                    raise
                return self.create_arpamar(fail=True)
            if self.current_index == self.ndata:
                break

        # 防止主参数的默认值被忽略
        if self.default_main_only and not self.main_args:
            self.main_args = analyse_args(
                self, self.self_args,
                self.separator, self.alconna.nargs, self.alconna.action
            )

        if self.current_index == self.ndata and (not self.need_main_args or (self.need_main_args and self.main_args)):
            return self.create_arpamar()

        data_len = self.rest_count(self.separator)
        if data_len > 0:
            exc = ParamsUnmatched("Unmatched params: {}".format(self.next_data(self.separator, pop=False)[0]))
        else:
            exc = ArgumentMissing("You need more data to analyse!")
        if self.is_raise_exception:
            raise exc
        return self.create_arpamar(fail=True, exception=exc)

    def create_arpamar(self, exception: Optional[BaseException] = None, fail: bool = False):
        result = Arpamar()
        result.head_matched = self.head_matched
        if fail:
            tb = traceback.format_exc(limit=1)
            result.error_info = repr(tb) if tb != 'NoneType: None\n' else exception
            result.error_data = self.recover_raw_data()
            result.matched = False
        else:
            result.matched = True
            result.encapsulate_result(self.header, self.main_args, self.options, self.subcommands)
        self.reset()
        return result


DisorderCommandAnalyser.add_arg_handler(MultiArg, multi_arg_handler)
DisorderCommandAnalyser.add_arg_handler(AntiArg, anti_arg_handler)
DisorderCommandAnalyser.add_arg_handler(UnionArg, union_arg_handler)
DisorderCommandAnalyser.add_arg_handler(ArgPattern, common_arg_handler)
DisorderCommandAnalyser.add_arg_handler(ObjectPattern, common_arg_handler)
DisorderCommandAnalyser.add_arg_handler(SequenceArg, common_arg_handler)
DisorderCommandAnalyser.add_arg_handler(MappingArg, common_arg_handler)
