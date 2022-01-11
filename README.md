# Python project configurator

Add configuration to your project - use parameters as attributes. 

## Features

- Support JSON and TOML file formats;
- Creates 'type' object which attributes are parameters from config;
- Any level of nesting - complex object will became an attribute of the parent object.
- Add new parameters as attributes on the fly;
- Store configuration object as a file;
- Encrypt stored configuration with a secret key.

## Usage

```py
# load configuration file from default path '$HOME/.everynet/config'
cfg = Config()
# load from custom path
cfg2 = Config(load_path='mypath/config.toml')
# or
cfg3 = Config()
cfg3.load('mypath/config.toml')

# add custom attributes
cfg.update({"key": "value"})
new_type = type("Type_attr", (BaseConfig,), {})
# even new types
cfg.update({"type_attr": new_type()})
# and update it's attributes
cfg.type_attr.update(sub_attr="sub_attr_value")
# save to the default path
cfg.save()
# remove object 
del cfg
# restore config file from default path
new_cfg = Config()
new_cfg.restore()
# check our attributes are loaded
assert new_cfg.key == "value"
assert new_cfg.type_attr.sub_attr
```

## Components

Configurator building blocks could be used separately to create custom converters. Module includes the following classes: MapDecoder, MapEncoder, BaseObject.

### MapDecoder

json.JSONDecoder extend class - recursivelly converts dictionaries to 'type' objects which attributes are (key,value) pairs. Keeps nesting - each subdictionary creates 'type' object and became attribute of the parent object.

Usage example:

```py
user_data = {
                "MyData": {
                    "pet":"cat",
                    "car": "vw",
                    "hobbies": {
                        "hockey": "wednesday", "planting": "sunday"
                    }
                }
            }

aliases = {"vw": "Volkswagen", "mb": "Mersedes-Benz"}

class MyDecoder(MapDecoder):
    def __init__(self):
        super().__init__(processor=self.process)

    def process(self, key, val):
        return aliases.get(val)
```

User data could be used as follow:

```py
>> converted = json.loads(json.dumps(user_data), cls=MyDecoder)
>> print(cls_data)
{'MyData': <class 'devutils.decode.Mydata'>}
>> print(cls_data["MyData"])
<class 'devutils.decode.Mydata'>
>> print(cls_data["MyData"].car)
Volkswagen
>> print(cls_data["MyData"].hobbies.hockey)
wednesday
```
