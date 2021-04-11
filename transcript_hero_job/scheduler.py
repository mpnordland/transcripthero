from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from transcript_hero_job import BatchProcessor


def main():

    scheduler = BlockingScheduler()
    # Add a scheduled job that runs every hour
    # to expire subscriptions (with 20min offset)
    batch_processor = BatchProcessor({})
    scheduler.add_job(
        batch_processor.expire_subscriptions,
        CronTrigger(hour='*', minute=20),
    )
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
