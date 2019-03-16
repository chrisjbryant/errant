# Auto format
.PHONY: auto_format
auto_format:
	isort -rc errant/
	black errant/ 
	@echo "Completed autoformating and sorting imports"

# # Linting
# .PHONY: lint
# lint:
# 	pylint -d locally-disabled,locally-enabled -f colorized errant
# 	@echo "Completed linting using pylint"

# Type-check
.PHONY: type_check
type_check:
	mypy errant --ignore-missing-imports
	@echo "Completed type-check using mypy"

# Unit-testing
# .PHONY: test
# test:
# 	pytest -c pytest.ini -v errant/
# 	@echo "Completed running unit-tests using pytest"