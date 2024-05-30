# makefile for ga4-user-admin
.DEFAULT_GOAL := help
-include .env
export

PROJECT_ID := disco-journeys
REGION := europe-west2
s_PRODUCT_NAME := discoprep
l_PRODUCT_NAME := disco-prep
image := $(REGION)-docker.pkg.dev/$(s_PRODUCT_NAME)
g_image := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(s_PRODUCT_NAME)/$(l_PRODUCT_NAME)
PORT ?= 8000

## run the code locally without docker
local-dev:
	gunicorn $(s_PRODUCT_NAME):app --log-level debug --reload

## build your docker image
docker-build:
	docker build -t $(g_image) .

## run your image as if deployed
docker-run:
	docker run \
	-v ~/.config/gcloud:/root/.config/gcloud \
	-e PORT=$(PORT) \
	-p $(PORT):$(PORT) \
	-e GOOGLE_CLOUD_PROJECT=${PROJECT} \
	$(g_image)

## runs a terminal in your latest image
docker-debug:
	docker run \
	-v ~/.config/gcloud:/root/.config/gcloud \
	-it $(g_image) /bin/bash

## clean up old containers
docker-clean:
	docker container prune -f

## build your image using gcloud builds
gcloud-build:
	gcloud builds submit . \
	--tag=$(g_image) \
	--region=$(REGION)

## deploy your latest image to Google Cloud Run
gcloud-deploy:
	gcloud run deploy $(l_PRODUCT_NAME) \
	--platform=managed \
	--image=${g_image} \
	--region=$(REGION)

## push your latest image to Docker
cloud-push:
	docker push $(image)

## build and deploy a virtual network to place your app behind authentication
vpc:
	gcloud compute network-endpoint-groups create $(s_PRODUCT_NAME)-iap-neg \
    	--project $(PROJECT_ID) \
    	--region=$(REGION) \
    	--network-endpoint-type=serverless  \
    	--cloud-run-service=$(l_PRODUCT_NAME)

	gcloud compute backend-services create $(s_PRODUCT_NAME)-iap-backend \
        --global 

	gcloud compute backend-services add-backend $(s_PRODUCT_NAME)-iap-backend \
    	--global \
    	--network-endpoint-group=$(s_PRODUCT_NAME)-iap-neg \
    	--network-endpoint-group-region=$(REGION)

	gcloud compute url-maps create $(s_PRODUCT_NAME)-iap-url-map \
	--default-service $(s_PRODUCT_NAME)-iap-backend

	gcloud compute addresses create $(s_PRODUCT_NAME)-iap-ip \
	--network-tier=PREMIUM \
	--ip-version=IPV4 \
	--global

	DOMAIN=$(gcloud compute addresses list --filter $(s_PRODUCT_NAME)-iap-ip --format='value(ADDRESS)').nip.io

	gcloud compute ssl-certificates create $(s_PRODUCT_NAME)-iap-cert \
	--description=$(s_PRODUCT_NAME)-iap-cert \
	--domains=$(DOMAIN) \
	--global

	gcloud compute target-https-proxies create $(s_PRODUCT_NAME)-iap-http-proxy \
	--ssl-certificates$(s_PRODUCT_NAME)-iap-cert \
	--url-map $(s_PRODUCT_NAME)-iap-url-map

	gcloud compute forwarding-rules create $(s_PRODUCT_NAME)-iap-forwarding-rule \
	--load-balancing-scheme=EXTERNAL \
	--network-tier=PREMIUM \
	--address=$(s_PRODUCT_NAME)-iap-ip \
	--global \
	--ports=443 \
	--target-https-proxy $(s_PRODUCT_NAME)-iap-http-proxy

	gcloud run services update $(l_PRODUCT_NAME) \
	--ingress internal-and-cloud-load-balancing \
	--region $(REGION)

	USER_EMAIL=$(gcloud config list account --format "value(core.account)")

	gcloud alpha iap oauth-brands create \
	--application_title=$(l_PRODUCT_NAME) \
	--support_email=$(USER_EMAIL)

	gcloud alpha iap oauth-clients create \
	projects/$(PROJECT_ID)/brands/$(PROJECT_NUMBER) \
	--display_name=$(l_PRODUCT_NAME)

	export CLIENT_NAME=$(gcloud alpha iap oauth-clients list \
	projects/$PROJECT_NUMBER/brands/$PROJECT_NUMBER --format='value(name)' \
	--filter="displayName:$(l_PRODUCT_NAME)")

	CLIENT_ID=${CLIENT_NAME##*/}

	CLIENT_SECRET=$(gcloud alpha iap oauth-clients describe $CLIENT_NAME --format='value(secret)')

	gcloud iap web enable --resource-type=backend-services \
	--oauth2-client-id=$CLIENT_ID \
	--oauth2-client-secret=$CLIENT_SECRET \
	--service=$(s_PRODUCT_NAME)-iap-backend

	gcloud compute ssl-certificates list --format='value(MANAGED_STATUS)'

	echo https://$(DOMAIN)


## Get help on all make commands
help:
	@echo "$$(tput bold)Available rules:$$(tput sgr0)"
	@echo
	@sed -n -e "/^## / { \
		h; \
		s/.*//; \
		:doc" \
		-e "H; \
		n; \
		s/^## //; \
		t doc" \
		-e "s/:.*//; \
		G; \
		s/\\n## /---/; \
		s/\\n/ /g; \
		p; \
	}" ${MAKEFILE_LIST} \
	| LC_ALL='C' sort --ignore-case \
	| awk -F '---' \
		-v ncol=$$(tput cols) \
		-v indent=25 \
		-v col_on="$$(tput setaf 6)" \
		-v col_off="$$(tput sgr0)" \
	'{ \
		printf "%s%*s%s ", col_on, -indent, $$1, col_off; \
		n = split($$2, words, " "); \
		line_length = ncol - indent; \
		for (i = 1; i <= n; i++) { \
			line_length -= length(words[i]) + 1; \
			if (line_length <= 0) { \
				line_length = ncol - indent - length(words[i]) - 1; \
				printf "\n%*s ", -indent, " "; \
			} \
			printf "%s ", words[i]; \
		} \
		printf "\n"; \
	}' \
	| more $(shell test $(shell uname) = Darwin && echo '--no-init --raw-control-chars')