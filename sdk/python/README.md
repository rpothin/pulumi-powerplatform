# Pulumi Power Platform SDK

The Pulumi Power Platform SDK allows you to manage [Microsoft Power Platform](https://powerplatform.microsoft.com/) resources using infrastructure as code.

## Installation

```bash
pip install pulumi-powerplatform
```

## Usage

```python
import pulumi_powerplatform as pp

env = pp.Environment(
    "dev",
    display_name="Development",
    location="unitedstates",
    environment_type="Sandbox",
)
```

## Documentation

For full documentation, visit the [GitHub repository](https://github.com/rpothin/pulumi-powerplatform).
