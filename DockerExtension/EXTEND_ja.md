# Docker and Azure IoT Hub 対応 
[OMRON Developer Hub](https://github.com/omron-devhub)の[環境センサーサンプル - USBで接続](https://github.com/omron-devhub/2jciebu-usb-raspberrypi)の拡張版です。 
最終的には、Azure IoT Edge Runtime化を目指します。 
現時点ではその一歩手前の、 
- サンプルコードのDocker化 
- Azure IoT Hubへの計測データの送信 

を実現しています。 Azure IoT Hubへの接続は、[Azure IoT SDK for Pythonのサンプルコード](https://github.com/Azure/azure-iot-sdk-python/blob/master/device/samples/iothub_client_sample.py)のエッセンスを抽出して埋め込んでいます。 

## 必要環境 
- Raspberry Pi 3 
- micro USB Class 10 以上、16GB 以上を推奨 
- [OMRON 環境センサー]() 

## 実行方法 
以下のステップでお試しください。作業は、全て Raspberry Pi上で実行します。 
### USBデバイス環境セットアップ 
以下のコマンドをRaspberry Piのシェル上で実行します。 
``` shell
$ sudo modprobe ftdi_sio 
$ sudo chmod 777 /sys/bus/usb-serial/drivers/ftdi_sio/new_id 
$ sudo echo 0590 00d4 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id
```
※この部分は、HWのセットアップなので、Dockerの実行に含めなくて良いかなと。

### 本リポジトリのクローンと Azure IoT Hub への接続情報の追加 
以下のコマンドでリポジトリをRaspberry Pi上にクローンします。 
```shell
$ git clone https://github.com/ms-iotkithol-jp/2jciebu-usb-raspberrypi.git 
$ cd 2jciebu-usb-raspberrypi
```
[Azure IoT Hubの作成、デバイスの登録に関するチュートリアル](https://docs.microsoft.com/ja-jp/azure/iot-hub/quickstart-send-telemetry-python) 等を参考に、Azure IoT Hub を作成し、"raspberrypi" という名前でデバイスを登録し、"HostName=<host_name>;DeviceId=raspberrypi;SharedAccessKey=<device_key>"という形式の接続文字列を取得します。 
この文字列を [sample_2jciebu-iotsdk.py](./sample_2jciebu-iotsdk.py) の48行目の <u>[Device Connection String]</u> の部分を上書きします。
```python
# String containing Hostname, Device Id & Device Key in the format:

# "HostName=<host_name>;DeviceId=<device_id>;SharedAccessKey=<device_key>"

CONNECTION_STRING = "[Device Connection String]"

```
### Docker Image のビルド 
実行用のDocker Imageを作ります。
```shell
$ sudo docker build -f raspberrypi-iotsdk.Dockerfile -t omronsensor .
```
これで、ローカルの Docker Hub 内に omronsensor という名前でDocker Image が作られます。

### Docker Image の実行 
以下のコマンドを実行すれば、USB環境センサーからデータを読み取り、IoT Hub にデータを送付します。 
```shell
$ sudo docker run --device=/dev/ttyUSB0:/dev/ttyUSB0 -v /sys/bus/usb-serial/:/sys/bus/usb-serial/ -t omronsensor
```

### センサーデータ取得とデータ送信の確認 
Docker Imageを起動したシェル上で、USB から取得したデータの表示が行われます。 
Azure IoT Hubへのデータ送信確認は、Device Explorer等を使ってください。使い方は、[こちら](https://github.com/Azure/azure-iot-sdk-csharp/tree/master/tools/DeviceExplorer)を参考にしてください。