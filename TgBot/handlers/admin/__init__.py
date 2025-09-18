def get_admin_router():
    from aiogram import Router

    from . import (
        commands,
        newsletter,
        notifications,
        settings
    )

    router = Router()

    router.include_routers(
        commands.router,
        newsletter.router,
        notifications.router,
        settings.router
    )

    return router