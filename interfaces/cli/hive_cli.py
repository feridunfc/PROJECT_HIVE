"""
PROJECT_HIVE Command Line Interface (Updated for API)
"""
import sys
import json
import asyncio
import aiohttp
import click
from typing import Optional, Dict, Any
from pathlib import Path
import time

# Configuration
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_API_KEY = "dev_key_123"


class HiveAPIClient:
    """Client for PROJECT_HIVE API."""

    def __init__(self, api_url: str = DEFAULT_API_URL, api_key: str = DEFAULT_API_KEY):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    async def run_pipeline(self, goal: str, pipeline_type: str = "t1") -> Dict[str, Any]:
        """Run a pipeline via API."""
        url = f"{self.api_url}/api/v1/run"

        payload = {
            "goal": goal,
            "pipeline_type": pipeline_type,
            "metadata": {
                "source": "cli",
                "timestamp": time.time()
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")

                return await response.json()

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status."""
        url = f"{self.api_url}/api/v1/tasks/{task_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")

                return await response.json()

    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get task result."""
        url = f"{self.api_url}/api/v1/tasks/{task_id}/result"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")

                return await response.json()

    async def list_tasks(self, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """List tasks."""
        url = f"{self.api_url}/api/v1/tasks?limit={limit}&offset={offset}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")

                return await response.json()

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a task."""
        url = f"{self.api_url}/api/v1/tasks/{task_id}/cancel"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")

                return await response.json()

    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        url = f"{self.api_url}/health"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()


@click.group()
@click.option('--api-url', default=DEFAULT_API_URL, help='API server URL')
@click.option('--api-key', default=DEFAULT_API_KEY, help='API key')
@click.pass_context
def cli(ctx, api_url, api_key):
    """PROJECT_HIVE CLI - Multi-Agent Orchestration Framework"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = HiveAPIClient(api_url=api_url, api_key=api_key)


@cli.command()
@click.argument('goal')
@click.option('--type', '-t', 'pipeline_type',
              type=click.Choice(['t0', 't1'], case_sensitive=False),
              default='t1', help='Pipeline type (t0=velocity, t1=fortress)')
@click.option('--wait', '-w', is_flag=True, help='Wait for completion')
@click.option('--timeout', default=300, help='Timeout in seconds (if waiting)')
@click.option('--output', '-o', type=click.Path(), help='Output file for result')
@click.pass_context
def run(ctx, goal, pipeline_type, wait, timeout, output):
    """Run a pipeline with the given goal."""
    client = ctx.obj['client']

    try:
        # Run pipeline
        click.echo(f"🚀 Starting {pipeline_type.upper()} pipeline...")
        click.echo(f"🎯 Goal: {goal}")

        result = asyncio.run(client.run_pipeline(goal, pipeline_type))
        task_id = result['task_id']

        click.echo(f"✅ Task submitted: {task_id}")
        click.echo(f"📊 Status: {result['status']}")
        click.echo(f"🔗 Poll URL: {ctx.obj['client'].api_url}/api/v1/tasks/{task_id}")

        if wait:
            click.echo("\n⏳ Waiting for completion...")
            start_time = time.time()

            while time.time() - start_time < timeout:
                status = asyncio.run(client.get_task_status(task_id))

                if status['status'] in ['completed', 'failed', 'cancelled']:
                    click.echo(f"\n✅ Task {status['status']}!")

                    # Get final result
                    result = asyncio.run(client.get_task_result(task_id))

                    if output:
                        with open(output, 'w') as f:
                            json.dump(result, f, indent=2)
                        click.echo(f"📁 Result saved to: {output}")
                    else:
                        click.echo(json.dumps(result, indent=2))

                    return

                click.echo(f"⏳ Current status: {status['status']}", nl=False)
                time.sleep(2)
                click.echo("\r", nl=False)

            click.echo(f"\n❌ Timeout after {timeout} seconds")

        else:
            click.echo("\n💡 Tip: Use `hive status <task_id>` to check progress")
            click.echo("💡 Tip: Use `hive result <task_id>` to get final result")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('task_id')
@click.pass_context
def status(ctx, task_id):
    """Check task status."""
    client = ctx.obj['client']

    try:
        status = asyncio.run(client.get_task_status(task_id))

        click.echo(f"📋 Task: {task_id}")
        click.echo(f"🎯 Goal: {status['goal']}")
        click.echo(f"📊 Type: {status['pipeline_type'].upper()}")
        click.echo(f"🔧 Status: {status['status']}")
        click.echo(f"🕐 Created: {status['created_at']}")

        if status.get('started_at'):
            click.echo(f"🚀 Started: {status['started_at']}")

        if status.get('completed_at'):
            click.echo(f"✅ Completed: {status['completed_at']}")

            duration = "N/A"
            if status['started_at'] and status['completed_at']:
                from datetime import datetime
                start = datetime.fromisoformat(status['started_at'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(status['completed_at'].replace('Z', '+00:00'))
                duration = str(end - start)

            click.echo(f"⏱️ Duration: {duration}")

        if status.get('error'):
            click.echo(f"❌ Error: {status['error']}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('task_id')
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.pass_context
def result(ctx, task_id, output):
    """Get task result."""
    client = ctx.obj['client']

    try:
        result = asyncio.run(client.get_task_result(task_id))

        if output:
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
            click.echo(f"📁 Result saved to: {output}")
        else:
            click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--limit', default=10, help='Number of tasks to show')
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show all tasks')
@click.pass_context
def list(ctx, limit, show_all):
    """List recent tasks."""
    client = ctx.obj['client']

    try:
        if show_all:
            limit = 1000

        tasks = asyncio.run(client.list_tasks(limit=limit))

        if not tasks.get('tasks'):
            click.echo("No tasks found")
            return

        click.echo(f"📋 Found {tasks['total']} tasks (showing {len(tasks['tasks'])}):")
        click.echo("")

        for task in tasks['tasks']:
            status_color = {
                'pending': '🟡',
                'running': '🟢',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '⭕'
            }.get(task['status'], '⚪')

            goal_preview = task['goal']
            if len(goal_preview) > 50:
                goal_preview = goal_preview[:47] + "..."

            click.echo(f"{status_color} {task['task_id'][:8]}... | {task['pipeline_type'].upper():<4} | "
                       f"{task['status']:<10} | {goal_preview}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('task_id')
@click.pass_context
def cancel(ctx, task_id):
    """Cancel a pending task."""
    client = ctx.obj['client']

    try:
        result = asyncio.run(client.cancel_task(task_id))
        click.echo(f"✅ {result['message']}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def health(ctx):
    """Check API health."""
    client = ctx.obj['client']

    try:
        health = asyncio.run(client.health_check())

        if health['status'] == 'healthy':
            click.echo("✅ API is healthy")
            click.echo(f"📊 Version: {health.get('version', 'N/A')}")

            if health.get('queue_stats'):
                stats = health['queue_stats']
                click.echo(f"📈 Queue: {stats.get('pending', 0)} pending, "
                           f"{stats.get('running', 0)} running, "
                           f"{stats.get('completed', 0)} completed")
        else:
            click.echo(f"❌ API is unhealthy: {health}")

    except Exception as e:
        click.echo(f"❌ Error connecting to API: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
def serve(host, port):
    """Start the API server."""
    import uvicorn

    click.echo(f"🚀 Starting PROJECT_HIVE API server on {host}:{port}")
    click.echo("📚 API documentation: http://localhost:8000/docs")
    click.echo("📊 Dashboard: http://localhost:8000/dashboard")
    click.echo("📈 Metrics: http://localhost:8000/metrics")
    click.echo("")
    click.echo("Press Ctrl+C to stop")

    uvicorn.run(
        "interfaces.api.main:app",
        host=host,
        port=port,
        log_level="info",
        reload=True
    )


if __name__ == "__main__":
    cli()