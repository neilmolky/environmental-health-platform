"""a place for all deployments to live and be executed as scripts"""

import asyncio

from prefect import aserve, deploy
from prefect.deployments.runner import RunnerDeployment

from backend.flows import met_office


async def adeploy_prod():
    """collect all deployments to deploy them remotely.

    async deployments must be awaited.

    this is user configured. When a pipeline is ready to deploy, add it here"""
    deployments: tuple[RunnerDeployment, ...] = (
        # await met_office.land_observation_stations.as_deployment("prod"),
    )
    deploy(*deployments)


async def aserve_local():
    """collect all deployments to serve them locally.

    async deployments must be awaited.

    this is user configured. When a pipeline is ready to test, add it here"""
    deployments: tuple[RunnerDeployment, ...] = (
        await met_office.land_observation_stations.as_deployment(),
    )
    await aserve(*deployments)


def deploy_prod():
    """deploy all flows for a kubernetes style deployment"""
    asyncio.run(adeploy_prod())


def serve_local():
    """deploy all flows for a docker-compose style deployment (as configurer in docker-compose.yml)"""
    asyncio.run(aserve_local())
