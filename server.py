"""nanobot — Telegram-only AI bot entry point."""

import argparse
import asyncio
from pathlib import Path

from loguru import logger

from lib.config.loader import load_config, get_data_dir
from lib.bus.queue import MessageBus
from lib.providers.litellm_provider import LiteLLMProvider
from lib.agent.loop import AgentLoop
from lib.channels.telegram import TelegramChannel
from lib.cron.service import CronService
from lib.cron.types import CronJob
from lib.bus.events import OutboundMessage


def main() -> None:
    parser = argparse.ArgumentParser(description="nanobot — Telegram AI bot")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.json")
    args = parser.parse_args()

    config = load_config(args.config)

    # --- Components ---
    bus = MessageBus()

    api_key = config.get_api_key()
    api_base = config.get_api_base()
    model = config.agents.defaults.model
    is_bedrock = model.startswith("bedrock/")

    if not api_key and not is_bedrock:
        logger.error("No API key configured. Set one in ~/.nanobot/config.json under providers")
        return

    provider = LiteLLMProvider(
        api_key=api_key,
        api_base=api_base,
        default_model=model,
    )

    # Cron
    cron_store_path = get_data_dir() / "cron" / "jobs.json"
    cron = CronService(cron_store_path)

    # Agent
    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=model,
        max_iterations=config.agents.defaults.max_tool_iterations,
        brave_api_key=config.tools.web.search.api_key or None,
        exec_config=config.tools.exec,
        cron_service=cron,
        restrict_to_workspace=config.tools.restrict_to_workspace,
    )

    # Cron callback
    async def on_cron_job(job: CronJob) -> str | None:
        response = await agent.process_direct(
            job.payload.message,
            session_key=f"cron:{job.id}",
            channel=job.payload.channel or "telegram",
            chat_id=job.payload.to or "direct",
        )
        if job.payload.deliver and job.payload.to:
            await bus.publish_outbound(OutboundMessage(
                channel=job.payload.channel or "telegram",
                chat_id=job.payload.to,
                content=response or "",
            ))
        return response

    cron.on_job = on_cron_job

    # Telegram channel
    tg_cfg = config.channels.telegram
    if not tg_cfg.enabled:
        logger.warning("Telegram is not enabled in config — enabling with current settings")
    telegram = TelegramChannel(tg_cfg, bus)

    # --- Outbound dispatcher ---
    async def dispatch_outbound() -> None:
        while True:
            try:
                msg = await asyncio.wait_for(bus.consume_outbound(), timeout=1.0)
                if msg.channel == "telegram":
                    try:
                        await telegram.send(msg)
                    except Exception as e:
                        logger.error(f"Error sending to Telegram: {e}")
                else:
                    logger.warning(f"Unknown channel: {msg.channel}")
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    # --- Run ---
    async def run() -> None:
        try:
            await cron.start()
            await asyncio.gather(
                agent.run(),
                telegram.start(),
                dispatch_outbound(),
            )
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            cron.stop()
            agent.stop()
            await telegram.stop()

    logger.info(f"Starting nanobot (model={model})")
    asyncio.run(run())


if __name__ == "__main__":
    main()
