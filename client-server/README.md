### Requires Python
Please have Python3.11 or newer installed on your machine. This has only been tested on Python3.11 and higher. I would reccomended looking at the README of the remote-visualization branch. You could possibly get away with an older Python version but that has not been tested.

### Requires VTK

The server has been ran and tested with the custom built VTK installed and built. **NOT** from pip install vtk. It might work with the VTK binary package installed from "pip install vtk" but not sure. If you are unsure of how to build VTK, I would look at the README in the remote-visualization branch.

### Using the virtual enviroment

Since I am using the VTK that was built and **NOT** VTK from pip install. I work and run my code and tests from the virtual enviroment. Therefore I would reccomended using the virutal enviroment to avoid potentinal issues. If you have not yet set up a virutal enviroment, I have listed the commands below.

```
python3.11 -m venv .venv
```

To activate the virtual enviroment:
```
source .venv/bin/activate
```

### Building the client

You will need to build the client before you can possibly continue. I have listed the commands to build the client.
```
cd vue-client-for-server
npm install
npm run build
```

### Start the server
You should start the server before starting the client. I have listed the commands to start the server (assuming you are using the virtual enviroment).

```
cd enter/path/to/client-server/server
python server_test_app.py
```

or if you do not want the server to open your broswer, as it is not necessary:
```
cd enter/path/to/client-server/server
python server_test_app.py --server
```

### Start the client
After starting the server, you can now start the client.
```
cd ../vue-client-for-server
npm run serve
```