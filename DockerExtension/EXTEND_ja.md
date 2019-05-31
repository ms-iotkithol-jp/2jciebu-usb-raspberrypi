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
$ sudo docker build -f DockerExtension/raspberrypi-iotsdk.Dockerfile -t omronsensor .
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

## Azure IoT Edge Module 対応 
Azure IoT Edge Runtime上で実行可能なImageを作ります。
```shell
$ sudo docker build -f DockerExtension/raspberrypi-iotedge.Dockerfile -t omronusbsensor .
```
これで、ローカルの Docker Hub 内に omronusbsensor という名前でIoT Edge 用Docker Image が作られます。 
できたImageをタグ付けして、Internet を介してアクセス可能な Docker Hub にプッシュします。 
```shell
$ sudo docker tag omronusbsensor public-docker-hub/omronusbsensor:1.0.0-arm32v7 
$ sudo docker push public-doncker-hub/omronusbsensor:1.0.0-arm32v7
```
これで準備完了です。<i>public-docker-hub</i>の部分は、ACRやDockerのURLです。<i>1.0.0-armv7</i>の部分は好みで構いません。 
個別のデバイスの IoT Edge への配置は、[IoT Edge への配置](https://docs.microsoft.com/ja-jp/azure/iot-edge/quickstart-linux) を参考にしてください。 
出力は、"sensorout" です。 
Azure Portal で、このモジュールを登録する場合は、[iotedge-module-creation-config.json](./iotedge-module-creation-config.json)を、コンテナーの作成オプションに追加します。 

※ 現状、USBデバイスの初期化処理は含んでいないので、Raspberry Pi 電源オン時に、
```shell
$ sudo systemctl stop iotedge 
$ ./device-initialization.sh 
$ sudo systemctl start iotedge
```
が必要です。 

## おまけ 
このモジュールがIoT Edge Runtimeに対して送信するセンサー読み取り結果に対して、例えば、Azure Stream Analytics on Edgeモジュールを適用できます。 
Azure Portal上で、Azure Stream Analytics on Edgeを作成し、
- 入力 ： EdgeHubInput 
― 出力 ： EdgeHubOutput 
と定義して、クエリーを 
```sql
with discomfortIndexValue as (
    select *, 0.81 * temperature + 0.01 * humidity * (0.99 * temperature - 14.3) + 46.3 as discomfortIndex
    FROM [EdgeHubInput]
)
SELECT
    measured_time,
        AnomalyDetection_SpikeAndDip(CAST(discomfortIndex AS float), 80, 120, 'spikes')
        OVER(LIMIT DURATION(second, 120)) AS SpikeAndDipScores
INTO
    [EdgeHubOutput]
FROM
    discomfortIndexValue
``` 

と定義して、IoT Edge にデプロイします。このクエリーはビルトイン関数のAnormaly Detection（簡単なAI）を使っているので、これだけで、センサーが計測した、温度と湿度を元に、不快指数を計測し、例えば、おやじがセンサーに吐息を吹きかけた様な、異常状態を検知し、IoT Hub に通知を送ることができます。 
