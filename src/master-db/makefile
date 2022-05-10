NO_COLOR=\033[0m
OK_COLOR=\033[32;01m
ERROR_COLOR=\033[31;01m
WARN_COLOR=\033[33;01m

GITHUB_SHA?="$(shell git rev-parse HEAD || :)"
define GA_SCRIPT
<script>
	window.ga=window.ga||function(){(ga.q=ga.q||[]).push(arguments)};ga.l=+new Date;
	ga('create', '$(GA_PROPERTY_ID)', 'auto');
	ga('send', 'pageview');
</script>
<script async src='https://www.google-analytics.com/analytics.js'></script>
endef
export GA_SCRIPT
define GA4_SCRIPT
<script async src="https://www.googletagmanager.com/gtag/js?id=$(GA4_PROPERTY_ID)"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', '$(GA4_PROPERTY_ID)');
</script>
endef
export GA4_SCRIPT

.PHONY: all add-analytics append-timestamp build build-json clean

all: clean build add-analytics append-timestamp
	@echo "$(OK_COLOR)==> Done!$(NOCOLOR)"

add-analytics: build
	@echo "$(OK_COLOR)==> Adding Google Analytics script to index.html!$(NOCOLOR)"
	@test "$(GA_PROPERTY_ID)" = "" \
	&& echo "$(WARN_COLOR)==> No property id set, skipping!$(NO_COLOR)" \
	|| echo "$$GA_SCRIPT" >> public/index.html
	@echo "$(OK_COLOR)==> Adding Google Analytics 4 script to index.html!$(NOCOLOR)"
	@test "$(GA4_PROPERTY_ID)" = "" \
	&& echo "$(WARN_COLOR)==> No property id set, skipping!$(NO_COLOR)" \
	|| echo "$$GA4_SCRIPT" >> public/index.html

append-timestamp: build
	@echo "$(OK_COLOR)==> Appending timestamp to index.html!$(NOCOLOR)"
	@echo "<!-- Deploy Timestamp: $(shell date --iso-8601=seconds) -->" >> public/index.html
	@echo "<!-- SHA: $(GITHUB_SHA) -->" >> public/index.html

build-json:
	@echo "$(OK_COLOR)==> Converting csv files into a single json… $(NO_COLOR)"
	@jq -sf src/data/db-csvtojson.jq src/data/*.json > 

build: clean build-json
	@echo "$(OK_COLOR)==> Building static page… $(NO_COLOR)"
	@mkdir public
	@cp src/index.html public/index.html
	@cp src/script.js public/script.js
	@cp src/worker.js public/worker.js
	@cp src/data/data.json public/data.json
	@cp src/data/additional/*.json public
	@cp -r src/data/alt/  public/alt
	@cp src/cfg.json public/cfg.json

clean:
	@echo "$(OK_COLOR)==> Cleaning project… $(NO_COLOR)"
	@rm -rf ./src/data/data.json
	@rm -rf ./public
