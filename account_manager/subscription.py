# -*- coding: utf-8 -*-

from loguru import logger  # https://github.com/Delgan/loguru
from telethon.errors import UserAlreadyParticipantError

from telethon.tl.functions.channels import JoinChannelRequest


async def subscription_telegram(client, target_username):
    """
    Подписка на группы каналы Telegram
    :param client: Telethon Client
    :param target_username: Имя канала Telegram
    :return: None
    """
    try:
        logger.info(f"🔗 Попытка присоединиться к целевой группе {target_username}...")
        await client(JoinChannelRequest(target_username))
        logger.success(f"✅ Успешно присоединился к целевой группе {target_username}")
    except UserAlreadyParticipantError:
        logger.info(f"ℹ️ Вы уже являетесь членом целевой группы {target_username}")

        entity = await client.get_entity(target_username)
        return entity.id
