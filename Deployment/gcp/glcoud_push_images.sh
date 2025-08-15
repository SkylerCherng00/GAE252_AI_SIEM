# /bin/bash
docker compose build

gcloud artifacts repositories create [repo_name] --repository-format=docker --location=[location_of_deploy_default_us-central1] --description="Docker repo for ai_siem images"

docker tag ai_siem/rpa_image:1.0.0 [location_of_deploy_default_us-central1]-docker.pkg.dev/testenv00/[repo_name]/rpa_image:1.0.0
docker push [location_of_deploy_default_us-central1]-docker.pkg.dev/testenv00/[repo_name]/rpa_image:1.0.0

docker tag ai_siem/msgcenter_image:1.0.0 [location_of_deploy_default_us-central1]-docker.pkg.dev/testenv00/[repo_name]/msgcenter_image:1.0.0
docker push [location_of_deploy_default_us-central1]-docker.pkg.dev/testenv00/[repo_name]/msgcenter_image:1.0.0

docker tag ai_siem/agent_image:1.0.0 [location_of_deploy_default_us-central1]-docker.pkg.dev/testenv00/[repo_name]/agent_image:1.0.0
docker push [location_of_deploy_default_us-central1]-docker.pkg.dev/testenv00/[repo_name]/agent_image:1.0.0
