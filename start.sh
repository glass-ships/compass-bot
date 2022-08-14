#!/usr/bin/env bash
export DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
#echo Script directory: $DIR
cd $DIR


showHelp() {
cat << EOF

Compass Bot
------------

Usage:
  ./start.sh [options]

Options:
  -h, --help,         Display this message
  -d, --dev           Run the test version of the bot
  -u, --upgrade       Install/upgrade required libraries
  -p, --pull          Pull upstream changes

EOF
}

# parse args
options=$(getopt -l "help,pull,update,dev:" -o "hpud" -a -- "$@")

eval set -- "$options"

pull=0
update=0
dev=0

while true
do
case $1 in
-h|--help) 
    showHelp
    exit 0
    ;;
-p|--pull)
    export pull=1
    ;;
-u|--update) 
    export update=1
    ;;
-d|--dev)
    export dev=1
    ;;
--)
    shift
    break;;
esac
shift
done

if [ $pull -eq 1 ]
then
    echo "Pulling upstream changes..."
    git stash
    git pull
fi

if [ $update -eq 1 ]
then
    echo "Upgrading required libraries..."
    pip install --upgrade -r requirements.txt
fi

if [ $dev -eq 1 ]
then
    echo "Starting test version of bot..."
    # ps axf | grep -i 'python src/main.py' | grep -v grep | awk '{print "kill -9 " $1}' | sh
    python src/main.py --dev
else
    echo "Starting production version of bot..."
    ps axf | grep -i 'python src/main.py' | grep -v grep | awk '{print "kill -9 " $1}' | sh # kill running instance
    nohup python src/main.py &
    disown $!
fi

