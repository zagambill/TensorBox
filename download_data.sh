#!/bin/bash
# This scripts downloads the ptb data and unzips it.

DIR="$( cd "$(dirname "$0")" ; pwd -P )"
cd $DIR

echo "Downloading..."

mkdir -p data && cd data
wget --continue https://citrineinformatics.box.com/s/wjzhi0bvchyhlwqql18ugf254kmv9s35
wget --continue https://citrineinformatics.box.com/s/tl8nhrqdww0y3p74230k57esuu15ph43
mkdir -p overfeat_rezoom && cd overfeat_rezoom
wget --continue https://citrineinformatics.box.com/s/53b4isa4hcvuzwgewvbnpxe6dakdpykr
cd ..
echo "Extracting..."
tar xf resnet_v1_101.tar.gz

if [[ "$1" == '--travis_tiny_data' ]]; then
    wget --continue http://russellsstewart.com/s/brainwash_tiny.tar.gz
    tar xf brainwash_tiny.tar.gz
    echo "Done."
else
    wget --continue https://stacks.stanford.edu/file/druid:sx925dc9385/brainwash.tar.gz
    tar xf brainwash.tar.gz
    echo "Done."
fi
