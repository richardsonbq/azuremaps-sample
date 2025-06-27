// Bicep template for deploying Flask Azure Maps App to Azure App Service and Azure Maps
// User can parametrize location for Azure Maps and App Service independently

param appName string = 'poc-azuremaps-${uniqueString(resourceGroup().id)}'
param appLocation string = resourceGroup().location
@allowed(['eastus','westus2','westeurope','northeurope','southeastasia','australiaeast','japaneast','uksouth','francecentral','germanywestcentral','brazilsouth','canadacentral','centralus','southcentralus','swedencentral','switzerlandnorth','uaenorth','norwayeast','koreacentral','indiacentral','polandcentral'])
param mapsLocation string = 'eastus'
param sku string = 'B1'
param mapsSkuName string = 'G2'

resource maps 'Microsoft.Maps/accounts@2023-06-01' = {
  name: '${appName}-maps'
  location: mapsLocation
  sku: {
    name: mapsSkuName
  }
  kind: 'Gen2'
  properties: {
    disableLocalAuth: false
    cors: {
      corsRules: [
        {
          allowedOrigins: ['*']
        }
      ]
    }
  }
}

resource plan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${appName}-plan'
  location: appLocation
  sku: {
    name: sku
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource webapp 'Microsoft.Web/sites@2022-03-01' = {
  name: appName
  location: appLocation
  kind: 'app,linux'
  properties: {
    serverFarmId: plan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      appSettings: [
        {
          name: 'AZURE_MAPS_KEY'
          value: maps.listKeys().primaryKey
        }
        {
          name: 'FLASK_ENV'
          value: 'production'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
      ]
      appCommandLine: 'gunicorn --bind=0.0.0.0 --timeout 600 app:app'
    }
    httpsOnly: true
  }
}

output webapp_url string = webapp.properties.defaultHostName
output azure_maps_account string = maps.name
