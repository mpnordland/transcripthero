#!/bin/sh

source venv/bin/activate
exec dramatiq transcript_hero_job.worker