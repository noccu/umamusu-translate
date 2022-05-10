NO_COLOR=\033[0m
OK_COLOR=\033[32;01m
ERROR_COLOR=\033[31;01m
WARN_COLOR=\033[33;01m
OUT_DIR=master-db
OUT_DATA_DIR=$(OUT_DIR)/data
TL_DIR=translations/master_db

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

all: build add-analytics append-timestamp
	@echo "$(OK_COLOR)==> Done!$(NOCOLOR)"

add-analytics: build
	@echo "$(OK_COLOR)==> Adding Google Analytics script to index.html!$(NOCOLOR)"
	@test "$(GA_PROPERTY_ID)" = "" \
	&& echo "$(WARN_COLOR)==> No property id set, skipping!$(NO_COLOR)" \
	|| echo "$$GA_SCRIPT" >> $(OUT_DIR)/index.html
	@echo "$(OK_COLOR)==> Adding Google Analytics 4 script to index.html!$(NOCOLOR)"
	@test "$(GA4_PROPERTY_ID)" = "" \
	&& echo "$(WARN_COLOR)==> No property id set, skipping!$(NO_COLOR)" \
	|| echo "$$GA4_SCRIPT" >> $(OUT_DIR)/index.html

append-timestamp: build
	@echo "$(OK_COLOR)==> Appending timestamp to index.html!$(NOCOLOR)"
	@echo "<!-- Deploy Timestamp: $(shell date --iso-8601=seconds) -->" >>  $(OUT_DIR)/index.html
	@echo "<!-- SHA: $(GITHUB_SHA) -->" >> $(OUT_DIR)/index.html

build:
	@echo "$(OK_COLOR)==> Building static page… $(NO_COLOR)"
	@jq -sf src/master-db/merge.jq $(TL_DIR)/*.json > $(OUT_DATA_DIR)/text_data.json
	@cp -r $(TL_DIR)/alt/  $(OUT_DATA_DIR)/alt

clean:
	@echo "$(OK_COLOR)==> Cleaning project… $(NO_COLOR)"
	@rm -rf ./$(OUT_DATA_DIR)
