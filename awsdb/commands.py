# -*- coding: utf-8 -*-
import asyncio
import traceback

import jsons
import requests
from discord import ChannelType, Client, Channel, Server, Message
from datetime import datetime

from awsdb import consts
from awsdb.utils import ASWDConfig
from awsdb.utils import Utils


class Command:
    """
    Botのコマンドクラス.
    """
    __config: ASWDConfig
    __has_args: bool
    __cmd: str

    @property
    def config(self):
        return self.__config

    @property
    def cmd(self):
        return self.__cmd

    @property
    def has_args(self):
        return self.__has_args

    def __init__(self, config, cmd, has_args):
        """
        コンストラクタ.
        :param config: コンフィグ管理インスタンス.
        :type config: ASWDConfig
        :param cmd: コマンド.
        :type cmd: str
        :param has_args: コマンドが変数を受け取るか.
        :type has_args: bool
        """
        self.__config = config
        self.__cmd = cmd
        self.__has_args = has_args

    def usage(self):
        """
        使い方を返却する.
        各コマンドで説明を実装してください.
        :return: コマンドの使い方
        :rtype: str
        """
        raise NotImplementedError('コマンドサブクラスでexecute_cmdを実装してください.')

    def is_call(self, msg):
        """
        コマンドが呼び出されたか.
        :param msg: 書き込まれたメッセージ
        :type msg: str
        :return: 処理結果
        :rtype: bool
        """
        return msg.startswith(self.cmd)

    def is_cmd_help(self, msg):
        """
        コマンドのヘルプが呼び出されたか.
        :param msg: 書き込まれたメッセージ
        :type msg: str
        :return: 判定結果
        :rtype: bool
        """
        return self.cmd + " /?" == msg

    def is_valid(self, message):
        """
        バリデーションを行う.
        引数なしの場合、メッセージとコマンドが一致するか.
        引数ありの場合、メッセージがコマンド+空白で始まり、かつ、メッセージ長がコマンド+空白以上か.
        :param message: Discordメッセージインスタンス
        :type message: Message
        :return: 判定結果
        :rtype: bool
        """
        if self.has_args:
            return message.content.startswith(self.cmd + " ") and len(self.cmd) + 1 < len(message.content)
        else:
            return message.content == self.cmd

    def valid_custom(self, message, args):
        """
        コマンド固有のバリデーションを行う.
        引数ありのコマンドの場合、このメソッドをオーバーライドしてバリデーションを実装してください.
        :param message: Discordメッセージインスタンス
        :type message: Message
        :param args: コマンド引数
        :type args: str
        :return: 検証失敗時のメッセージ.検証成功の場合はNone.
        :rtype: str
        """
        return None

    async def execute(self, message):
        """
        コマンドを実行する.
        :param message: Discordメッセージインスタンス
        :type message: Message
        """
        print(self.cmd + " call.")
        if not message and not message.content:
            print("【エラー】Discordからコマンドが受け取れません. 再度入力してください.")
            return False
        if self.is_cmd_help(message.content):
            await self.send_message(message.channel, self.usage())
            print(self.cmd + " show help.")
            return False
        if not self.is_valid(message):
            msg = "コマンドが正しくありません.\n" + self.usage()
            await self.send_message(message.channel, msg)
            print(self.cmd + " failed valid.")
            return False
        args = message.content[len(self.cmd) + 1:]
        valid_msg = self.valid_custom(message, args)
        if valid_msg:
            msg = valid_msg + "\n" + self.usage()
            await self.send_message(message.channel, msg)
            print(self.cmd + " failed valid_custom.")
            return False
        await self.execute_cmd(message, args)
        print(self.cmd + " called.")

    async def execute_cmd(self, message, args):
        """
        コマンド固有の処理を実行する.
        各コマンドはメインの処理をここに実装してください.
        :param message: Discordメッセージインスタンス
        :type message: Message
        :param args: コマンド引数
        :type args: str
        :return: 処理結果
        :rtype: bool
        """
        raise NotImplementedError('コマンドサブクラスでexecute_cmdを実装してください.')

    async def send_message(self, channel, msg):
        """
        メッセージを送信する.
        :param channel: メッセージ送信先Channelインスタンス
        :type channel: ChannelType
        :param msg: 送信するメッセージ
        :type msg: str
        :return: 処理結果
        :rtype: bool
        """
        await Utils.send_message(self.config.client, channel, msg)


class AllCommand(Command):
    """
    全コマンドを扱うコマンドクラス
    """

    __cmd_list: list

    @property
    def cmd_list(self):
        return self.__cmd_list

    def __init__(self, config, cmd, has_args, cmd_list):
        super().__init__(config, cmd, has_args)
        self.__cmd_list = cmd_list


class CommandManager:
    """
    コマンド管理クラス.
    コマンド実行はこのクラスの execute() にメッセージを食わせる.
    """

    __config: ASWDConfig
    __cmd_list: list
    __help_cmd: Command

    def __init__(self, config):
        """
        コンストラクタ.
        コマンドクラス追加時は __cmd_list にコマンドインスタンスを追加すること.
        :param config: コンフィグ管理インスタンス
        :type config: ASWDConfig
        """

        self.__config = config
        self.__cmd_list = [
            StartCommand(config),
            StopCommand(config),
            AddEnemyCommand(config),
            DelEnemyCommand(config),
            ListEnemyCommand(config),
            AddBlackListCommand(config),
            DelBlackListCommand(config),
            ListBlackListCommand(config),
            AddServerCommand(config),
            DelServerCommand(config),
            StatusCommand(config),
            SetWatchWorldCommand(config),
            SetWatchIntervalCommand(config),
            SetPlayerSbnCountCommand(config),
            FuckYeahCommand(config)
        ]
        self.__help_cmd = HelpCommand(config, self.__cmd_list)
        self.__cmd_list.append(self.__help_cmd)

    async def execute(self, message):
        """
        コマンド実行.
        :param message: Discordのメッセージインスタンス
        :type message: Message
        :return: 処理結果
        :rtype: bool
        """

        # コマンド呼び出し判定
        if not message.content.startswith("/"):
            return False

        # コマンド判定
        call_cmd = None
        for cmd in self.__cmd_list:
            if cmd.is_call(message.content):
                call_cmd = cmd
                break
        if not call_cmd:
            # コマンドが存在しない場合ヘルプ表示
            msg = "コマンドが正しくありません.\n" + self.__help_cmd.usage()
            await Utils.send_message(self.__config.client, message.channel, msg)
            return False

        return await call_cmd.execute(message)


class HelpCommand(AllCommand):
    """
    ヘルプを表示する.
    """

    def __init__(self, config, cmd_list):
        ret = []
        for cmd in cmd_list:
            if type(cmd) == HelpCommand:
                continue
            ret.append(cmd)
        super().__init__(config, "/?", False, ret)

    def usage(self):
        msg = "`/?`" \
              "\nヘルプを表示します.\n/start /? のように入力するとコマンドのヘルプを表示します."
        return msg

    async def execute_cmd(self, message, args):
        ret = []
        ret.append(self.usage() + "\n")
        for cmd in self.cmd_list:
            ret.append(cmd.usage() + "\n")
        msg = "\n".join(ret)
        await self.send_message(message.channel, msg)
        return True


class StartCommand(Command):
    """
    サーバ監視開始コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/start", False)

    def usage(self):
        msg = "`/start`" \
              "\nサーバの監視を開始します." \
              "\n指定時間ごとにサーバやプレイヤー情報を取得して各報告用チャンネルに出力し、" \
              "プレイヤーが急増した場合や敵プレイヤーが監視サーバに侵入した場合に通知します."
        return msg

    def valid_custom(self, message, args):
        if self.config.is_watch_started:
            return "監視継続します."

    async def execute_cmd(self, message, args):
        msg = "監視開始."
        await self.send_message(message.channel, msg)

        self.config.is_watch_started = True
        self.config.last_servers_info = {}
        self.config.enemy_notice_server_names.clear()
        while self.config.is_watch_started:
            try:
                watch_server_names = Utils.get_watch_server_names(self.config.client)

                # サーバ情報取得
                try:
                    print('ClusterServer情報取得開始.')
                    cluster_servers_info_json = requests.get(
                        consts.URL_CLUSTER_SERVER.format(self.config.watch_world)).text
                    print("ClusterServer情報取得完了.")
                    if not cluster_servers_info_json:
                        msg = '【エラー】サーバ情報jsonが空. 再度実行.'
                        print(msg)
                        await self.send_message(message.channel, msg)
                        await asyncio.sleep(self.config.watch_interval)
                        continue
                except Exception as e:
                    with open(consts.LOG_FILE, 'a') as f:
                        traceback.print_exc(file=f)
                    msg = '【エラー】サーバ情報取得失敗. サーバダウンかも. 再度実行.'
                    print(msg)
                    await self.send_message(message.channel, msg)
                    await asyncio.sleep(self.config.watch_interval)
                    continue
                print("ClusterServer情報取得成功.")

                # サーバ情報を監視サーバ毎に格納
                cluster_servers_info_dict = jsons.loads(cluster_servers_info_json)
                servers_info = {}

                for server_name in watch_server_names:
                    server_id = Utils.get_server_id(self.config.watch_world, server_name)
                    cluster_server_info = Utils.get_object("id", server_id, cluster_servers_info_dict)
                    if not cluster_server_info:
                        continue
                    player_count = cluster_server_info["player_count"]

                    # 監視サーバ毎プレイヤー情報取得
                    try:
                        print('ServerPlayer情報取得開始.')
                        server_player_info_json = requests.get(
                            consts.URL_SERVER_PLAYER.format(server_id)).text
                        print("ServerPlayer情報取得完了.")
                        if not server_player_info_json:
                            msg = '【エラー】プレイヤー情報jsonが空. 再度実行.'
                            print(msg)
                            await self.send_message(message.channel, msg)
                            await asyncio.sleep(self.config.watch_interval)
                            continue
                    except Exception as e:
                        with open(consts.LOG_FILE, 'a') as f:
                            traceback.print_exc(file=f)
                        msg = '【エラー】プレイヤー情報取得失敗. サーバダウンかも. 再度実行.'
                        print(msg)
                        await self.send_message(message.channel, msg)
                        await asyncio.sleep(self.config.watch_interval)
                        continue
                    print("ServerPlayer情報取得成功.")

                    players = jsons.loads(server_player_info_json)
                    player_sbn_count = 0
                    last_server_info = None
                    if len(self.config.last_servers_info) != 0 and server_name in self.config.last_servers_info:
                        last_server_info = self.config.last_servers_info[server_name]
                    if last_server_info is not None:
                        last_player_count = last_server_info["player_count"]
                        player_sbn_count = player_count - last_player_count if last_player_count is not None and 0 < last_player_count else -1
                    enemy_players = []
                    if not players or "data" in players:
                        print("【WARN 】プレイヤー情報なし.")
                    else:
                        for enemy in self.config.enemy_list:
                            for player in players:
                                player_name = str(player["name"])
                                if not player_name or player_name.upper().find(enemy.upper()) == -1:
                                    continue
                                enemy_players.append("{}({})".format(player["name"], self.config.enemy_list[enemy]))

                    servers_info[server_name] = {
                        "server_name": server_name,
                        'player_count': player_count,
                        "player_sbn_count": player_sbn_count,
                        "enemy_players": enemy_players
                    }

                # サーバ情報を元に通知
                timestr = datetime.now().strftime("%m/%d %H:%M")
                tgt_channels = Utils.get_channels(self.config.client)
                print("get_channels end. tgt_channels.len=", len(tgt_channels) > 0)
                if len(tgt_channels) > 0:
                    for tgt_channel in tgt_channels:
                        if tgt_channel.name.upper() not in servers_info:
                            msg = "{}　{}　データ取得エラー.".format(timestr, tgt_channel.name.upper())
                            await self.send_message(tgt_channel, msg)
                            continue
                        server_info = servers_info[tgt_channel.name.upper()]
                        if server_info is None:
                            continue

                        server_name = server_info["server_name"]
                        player_count = server_info["player_count"]
                        player_sbn_count = server_info["player_sbn_count"]
                        enemy_players = server_info["enemy_players"]

                        # 定例メッセージ送信
                        msg = "{}　{}　人数:{}　敵:{}人 {}".format(timestr, server_name, player_count, len(enemy_players),
                                                            enemy_players)
                        await self.send_message(tgt_channel, msg)

                        # 警告メッセージ(人数急増)
                        if self.config.player_sbn_count <= player_sbn_count:
                            msg = "@everyone サーバが {}人増えて {}人に急増. 敵襲か？".format(player_sbn_count, player_count)
                            await self.send_message(tgt_channel, msg)

                        # 警告メッセージ(ブラックリスト対象の侵入)
                        if len(enemy_players) > 0:
                            if server_name not in self.config.enemy_notice_server_names:
                                msg = "@everyone ブラックリストの {} がやってきたぞ.".format(', '.join(enemy_players))
                                await self.send_message(tgt_channel, msg)
                                self.config.enemy_notice_server_names.append(server_name)

                        # 通常メッセージ(ブラックリスト対象者0になった)
                        if len(enemy_players) == 0 and server_name in self.config.enemy_notice_server_names:
                            msg = "ブラックリストのやつらはどこかへ行ったようだ."
                            await self.send_message(tgt_channel, msg)
                            self.config.enemy_notice_server_names.remove(server_name)

                # 今回取得したサーバ情報を保持
                self.config.last_servers_info = servers_info
            except Exception as e:
                with open(consts.LOG_FILE, 'a') as f:
                    traceback.print_exc(file=f)
                msg = '【エラー】処理続行. 複数回発生したら/stopして.'
                print(msg)
                await self.send_message(message.channel, msg)

            await asyncio.sleep(self.config.watch_interval)
        return True


class StopCommand(Command):
    """
    サーバ監視終了コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/stop", False)

    def usage(self):
        msg = "`/stop`" \
              "\nサーバの監視を終了します."
        return msg

    async def execute_cmd(self, message, args):
        self.config.is_watch_started = False
        await self.send_message(message.channel, "監視終了.")
        return True


class AddEnemyCommand(Command):
    """
    敵プレイヤー追加コマンド.
    """

    def __init__(self, config, cmd=None, has_args=False):
        super().__init__(config, cmd if cmd else "/add enemy", has_args if has_args else True)

    def usage(self):
        msg = "`/add enemy [プレイヤー名] [カンパニー名]`" \
              "\n敵プレイヤーを追加します." \
              "\n追加した敵プレイヤーは監視中のサーバに現れた場合、通知します." \
              "\nカンパニー名は省略可能です." \
              "\n名前やカンパニー名に空白が存在する場合、ダブルクォートで囲んでください.(例: /add enemy \"player name\" \"company name\")" \
              "\n敵プレイヤー名は大文字小文字問わずあいまい検索で判定します.(例: Bcd を追加した場合、abcde というプレイヤーに一致します.)"
        return msg

    def valid_custom(self, message, args):
        if not args:
            return "プレイヤー名を正しく入力してください."

    async def execute_cmd(self, message, args):
        arg_list = self.split_args(args)
        pname = arg_list[0] if len(arg_list) >= 1 else ""
        cname = arg_list[1] if len(arg_list) >= 2 else ""
        self.config.add_enemy(pname, cname)
        msg = "敵プレイヤーに追加しました."
        await self.send_message(message.channel, msg)
        return True

    def split_args(self, args):
        """
        引数を分割する.
        :param args: 引数
        :type args: str
        :return: 分割した引数
        :rtype: list of str
        """
        ret = []
        if args.find("\"") >= 0:
            arg = ""
            in_dq = False
            for s in args:
                if s == " " and not in_dq:
                    ret.append(arg.strip())
                    arg = ""
                    continue
                if s == "\"":
                    in_dq = not in_dq
                    continue
                arg += s
            if arg:
                ret.append(arg.strip())
        else:
            ret = args.split(" ")
            if not ret:
                return None
        return ret


class AddBlackListCommand(AddEnemyCommand):
    """
    敵プレイヤー追加コマンド.
    今までのバージョンと同じように/add blで登録できるようにする.
    """

    def __init__(self, config):
        super().__init__(config, "/add bl", True)

    def usage(self):
        msg = "`/add bl [プレイヤー名] [カンパニー名]`" \
              "\n敵プレイヤーを追加します." \
              "\n/add enemy と同様の処理を行います."
        return msg


class DelEnemyCommand(Command):
    """
    敵プレイヤー削除コマンド.
    """

    def __init__(self, config, cmd=None, has_args=False):
        super().__init__(config, cmd if cmd else "/del enemy", has_args if has_args else True)

    def usage(self):
        msg = "`/del enemy [プレイヤー名] [カンパニー名]`" \
              "\n敵プレイヤーを削除します."
        return msg

    def valid_custom(self, message, args):
        if not args:
            return "プレイヤー名を正しく入力してください."
        if args not in self.config.enemy_list:
            return "敵プレイヤーは存在しません."

    async def execute_cmd(self, message, args):
        self.config.del_enemy(args)
        msg = "敵プレイヤーを削除しました."
        await self.send_message(message.channel, msg)
        return True


class DelBlackListCommand(DelEnemyCommand):
    """
    敵プレイヤー削除コマンド.
    今までのバージョンと同じように/del bl で削除できるようにする.
    """

    def __init__(self, config):
        super().__init__(config, "/del bl", True)

    def usage(self):
        msg = "`/del bl [プレイヤー名] [カンパニー名]`" \
              "\n敵プレイヤーを削除します." \
              "\n/del enemy と同様の処理を行います."
        return msg


class ListEnemyCommand(Command):
    """
    敵プレイヤー一覧表示コマンド.
    """

    def __init__(self, config, cmd=None, has_args=False):
        super().__init__(config, cmd if cmd else "/list enemy", has_args if has_args else False)

    def usage(self):
        msg = "`/list enemy`" \
              "\n敵プレイヤーの一覧を表示します."
        return msg

    async def execute_cmd(self, message, args):
        msg = "敵プレイヤー: {}".format(self.config.list_enemy())
        await self.send_message(message.channel, msg)
        return True


class ListBlackListCommand(ListEnemyCommand):
    """
    敵プレイヤー一覧表示コマンド.
    """

    def __init__(self, config, cmd=None, has_args=False):
        super().__init__(config, cmd if cmd else "/list bl", has_args if has_args else False)

    def usage(self):
        msg = "`/list bl`" \
              "\n敵プレイヤーの一覧を表示します."\
              "\n/list enemy と同様の処理を行います."
        return msg


class AddServerCommand(Command):
    """
    監視対象サーバ追加コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/add server", True)

    def usage(self):
        msg = "`/add server [サーバー名(A1-O15)]`" \
              "\n監視対象とするサーバを追加します." \
              "\n追加するとDiscordにサーバー監視報告用のチャンネルを作成します."
        return msg

    def valid_custom(self, message, args):
        if not args or not Utils.exists_server_name(args.upper()):
            return "サーバー名にA1～O15を設定してください."
        if Utils.exists_channel(message.server, args):
            return "対象サーバは既に監視対象です."

    async def execute_cmd(self, message, args):
        print("サーバ監視報告チャンネル作成. name={}".format(args.upper()))
        await self.config.client.create_channel(message.server, args.upper(), type=ChannelType.text)
        print("サーバ監視報告チャンネル作成完了.")
        msg = "{}チャンネル追加. 監視情報はそこに出力します.".format(args.upper())
        await self.send_message(message.channel, msg)
        return True


class DelServerCommand(Command):
    """
    監視対象サーバ削除コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/del server", True)

    def usage(self):
        msg = "`/del server　[サーバー名(A1-O15)]`" \
              "\n監視対象とするサーバを削除します." \
              "\n削除するとDiscordにサーバー監視報告用のチャンネルもあわせて削除します."
        return msg

    def valid_custom(self, message, args):
        if not args or len(args) != 2 or not Utils.exists_server_name(args.upper()):
            return "サーバー名にA1～O15を設定してください."
        if not Utils.exists_channel(message.server, args):
            return "対象サーバは監視対象ではありません."

    async def execute_cmd(self, message, args):
        print("サーバ監視報告チャンネル削除. name={}".format(args.upper()))
        channel = Utils.exists_channel(message.server, args)
        await self.config.client.delete_channel(channel)
        print("サーバ監視報告チャンネル作成完了.")
        msg = "{}チャンネル削除.".format(args.upper())
        await self.send_message(message.channel, msg)
        return True


class StatusCommand(Command):
    """
    ステータス表示コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/status", False)

    def usage(self):
        msg = "`/status`" \
              "\n各設定値や監視状態など現在の状態を表示します."
        return msg

    async def execute_cmd(self, message, args):
        msg_started = "監視中" if self.config.is_watch_started else "監視していません"
        msg = "監視状態:{}\n監視ワールド:{} {}\n監視間隔(秒):{}\n通知対象プレイヤー増加数:{}\n敵プレイヤー:{}\n敵侵入中サーバ:{}".format(msg_started,
                                                                                                 self.config.watch_world,
                                                                                                 Utils.get_value(
                                                                                                     "id",
                                                                                                     self.config.watch_world,
                                                                                                     "name",
                                                                                                     consts.CLUSTERS),
                                                                                                 self.config.watch_interval,
                                                                                                 self.config.player_sbn_count,
                                                                                                 self.config.list_enemy(),
                                                                                                 self.config.enemy_notice_server_names)
        await self.send_message(message.channel, msg)
        return True


class SetWatchWorldCommand(Command):
    """
    監視ワールド設定コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/set world", True)

    def usage(self):
        msg = "`/set world　[1-4]`" \
              "\n監視ワールドを設定します." \
              "\n設定は数字で入力してください" \
              "\n(1: NA PvE, 2: NA PvP, 3: EU PvE, 4: EU PvP)"
        return msg

    def valid_custom(self, message, args):
        if not args or not args.isdecimal():
            return "1から4の数字を設定してください."
        int_val = int(args)
        if int_val < 1 or 4 < int_val:
            return "1から4の数字を設定してください."

    async def execute_cmd(self, message, args):
        int_val = int(args)
        self.config.watch_world = int_val
        msg = "監視ワールドを {} に設定しました.".format(Utils.get_value("id", int_val, "name", consts.CLUSTERS))
        await self.send_message(message.channel, msg)
        return True


class SetWatchIntervalCommand(Command):
    """
    監視間隔設定コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/set interval", True)

    def usage(self):
        msg = "`/set interval [秒]`" \
              "\n監視間隔(秒)を設定します." \
              "\n指定された間隔ごとにサーバ情報やプレイヤー情報を取得し出力します."
        return msg

    def valid_custom(self, message, args):
        if not args or not args.isdecimal():
            return "監視間隔に数値を設定してください."

    async def execute_cmd(self, message, args):
        int_val = int(args)
        if int_val < 30:
            msg = "指定した数値が30秒未満のため、30秒を設定します."
            await self.send_message(message.channel, msg)
            int_val = 30
        self.config.watch_interval = int_val

        msg = "監視間隔を{}秒に設定しました.".format(int_val)
        await self.send_message(message.channel, msg)
        return True


class SetPlayerSbnCountCommand(Command):
    """
    通知対象プレイヤー増加数設定コマンド.
    """

    def __init__(self, config):
        super().__init__(config, "/set player_count", True)

    def usage(self):
        msg = "`/set player_count [人数]`" \
              "\nサーバのプレイヤーが一気に増加した場合に通知を行う際の閾値を設定します." \
              "\n前回と今回のサーバ人数を比較し、この設定値以上になった場合にサーバ監視報告チャンネルに通知します."
        return msg

    def valid_custom(self, message, args):
        if not args:
            return "プレイヤー増加数を数値で設定してください."

    async def execute_cmd(self, message, args):
        int_val = int(args)
        if int_val < 3:
            msg = "指定した数値が3人未満のため、3人を設定します."
            await self.send_message(message.channel, msg)
            int_val = 3
        self.config.player_sbn_count = int_val

        msg = "通知対象プレイヤー増加数を{}人に設定しました.".format(int_val)
        await self.send_message(message.channel, msg)
        return True


class FuckYeahCommand(Command):
    """
    Fuck YEAH !!
    """

    def __init__(self, config):
        super().__init__(config, "/fuck", True)

    def usage(self):
        msg = "`/fuck xxx`" \
              "\nFuck YEAH !!"
        return msg

    async def execute_cmd(self, message, args):
        msg = "Fuck YEAH !!"
        await self.send_message(message.channel, msg)
        # msg = "https://www.youtube.com/watch?v=IhnUgAaea4M&feature=youtu.be&t=8"
        msg = "https://clips.twitch.tv/PrettiestFaintUdonPoooound"
        await self.send_message(message.channel, msg)
        return True
