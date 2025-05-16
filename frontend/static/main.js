const log = document.getElementById("log");
const socket = new WebSocket(`ws://${location.host}/ws`);

socket.onmessage = (event) => {
  const msg = document.createElement("div");
  msg.className = "bg-white text-blue-800 p-2 rounded-xl max-w-xs shadow self-start";
  msg.textContent = event.data;
  log.appendChild(msg);
  log.scrollTop = log.scrollHeight;
};

function sendMessage(event) {
  event.preventDefault();  // prevent form reload

  const input = document.getElementById("msgInput");
  const message = input.value;
  if (!message.trim()) return;

  const msg = document.createElement("div");
  msg.className = "bg-blue-500 text-white p-2 rounded-xl max-w-xs shadow self-end ml-auto";
  msg.textContent = message;
  log.appendChild(msg);
  log.scrollTop = log.scrollHeight;

  socket.send(message);
  input.value = "";
}
