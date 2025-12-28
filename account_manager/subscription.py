# -*- coding: utf-8 -*-

from telethon.tl.functions.channels import JoinChannelRequest


async def subscription_telegram(client, target_username):
    """
    Подписка на группы каналы Telegram
    :param client: Telethon Client
    :param target_username: Имя канала Telegram
    :return: None
    """
    logger.info(f"🔗 Попытка присоединиться к целевой группе {target_username}...")
    await client(JoinChannelRequest(target_username))
