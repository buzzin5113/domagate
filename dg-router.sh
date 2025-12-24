#!/bin/sh
SCRIPT_NAME="dg-router.sh"
PATH="/opt/sbin:/opt/bin:/opt/usr/sbin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin"


ALLOWED_USERS="user1 user2"
BOT_NAME="/botbotbot"

ALL_OUTPUT=""

function check_running {
  cd /opt/root
  if pgrep -f "$SCRIPT_NAME" | grep -v $$; then
    echo " $SCRIPT_NAME already running!"
    exit 1
  fi
}


function check_username {

  if echo $ALLOWED_USERS | grep -w -q $USERNAME; then
    echo "Found: $USERNAME is in allowed users"
  else
    echo "User $USERNAME not found";
    continue;
  fi
}

function set_update_id {

  let UPDATE_ID++
  OUTPUT=`curl -s https://api.telegram.org/botXXX/getUpdates?offset=${UPDATE_ID}`
}


function check_messages {
  if  [ ${#MESSAGES} -lt 50 ]; then
    echo "No message";
    exit;
  else
    echo "Start work"
  fi

}

function check_dest {
  DEST=`echo ${TEXT} | cut -d " " -f1`
  if [[ $DEST == $BOT_NAME ]]; then
    echo "Bot name is ok"
  else
    echo "Bot name is wrong";
    set_update_id;
    continue;
  fi

}

function run_command {
  echo "Run command..."
  COMMAND="echo | ${TEXT:${#BOT_NAME}}"
  echo $COMMAND
  #ALL_OUTPUT=$(${COMMAND} 2>&1)
  ALL_OUTPUT=$(/bin/sh -c "$COMMAND 2>&1")
  echo $ALL_OUTPUT

}

function send_answer {
  echo "Send answer..."
  ANSWER=`curl -s -X POST -d chat_id=$CHAT_ID -d text="$ALL_OUTPUT" "https://api.telegram.org/botXXX/sendMessage"`
  ANSWER_OK=$(echo $ANSWER | jq '.ok')
  if [[ $ANSWER_OK == "false" ]]; then
    curl -s -X POST -d chat_id=$CHAT_ID -d text="$ANSWER" "https://api.telegram.org/botXXX/sendMessage"
  else
    echo "Send ok"
  fi
}


# MAIN

echo "Running"
check_running

while true; do

  MESSAGES=`curl -s https://api.telegram.org/botXXX/getUpdates`

  check_messages

  UPDATE_ID=$(echo $MESSAGES | jq '.result.[0].update_id')
  CHAT_ID=$(echo $MESSAGES   | jq '.result.[0].message.chat.id')
  USERNAME=$(echo $MESSAGES  | jq '.result.[0].message.from.username' | tr -d '"')
  TEXT=$(echo $MESSAGES      | jq '.result.[0].message.text' | tr -d '"')

  echo $UPDATE_ID
  echo $CHAT_ID
  echo $USERNAME
  echo $TEXT

  # Check username
  check_username

  # Check destination (it's me)
  check_dest

  # Run command
  run_command

  # Send answer
  send_answer

  # Set UPDATE_ID
  set_update_id

done
