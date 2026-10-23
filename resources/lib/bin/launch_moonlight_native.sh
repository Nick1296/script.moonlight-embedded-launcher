#!/usr/bin/env bash
. /etc/profile


function kill_kodi(){
	echo "Killing kodi"
	if systemctl list-units | grep -q kodi; then
		systemctl stop kodi
	else
		pkill kodi
	fi
}

function start_kodi(){
	echo "Restarting kodi"
	if systemctl list-units | grep -q kodi; then
		systemctl --no-block start kodi
	else
		kodi-standalone &
		disown
	fi
}

# Get optional arguments/flags (should be specified before standard arguments)
optstring=':qi:c:'
while getopts ${optstring} arg; do
  case ${arg} in
  c)
    customflag=${OPTARG}
    ;;
  i)
    hostip=${OPTARG}
    ;;
  q)
    quitflag='-quitappafter'
    ;;
  esac
done
shift $((OPTIND - 1))

# Get standard stream parameters
if [ -z "$1" ]; then
  echo "Error, please specify resolution (720,1080 or 4k)...exiting"
  exit 1
else
  res="$1"
fi
if [ -z "$2" ]; then
  echo "Error, please specify frame rate (30,60)...exiting"
  exit 1
else
  fps="$2"
fi
if [ -z "$3" ]; then
  echo "Error, please specify bitrate...exiting"
  exit 1
else
  bitrate="$3"
fi
if [ -z "$4" ]; then
  echo "Error, please specify game...exiting"
  exit 1
else
  game="$4"
fi

kill_kodi # Must close kodi for proper video display

echo "Starting moonlight"
moonlight stream -"$res" -fps "$fps" -bitrate "$bitrate" "$quitflag" $customflag -app "$game" "$hostip"

start_kodi # Reopen kodi
