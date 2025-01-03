const axios = require("axios");
const fs = require("fs");
const path = require("path");
const FormData = require("form-data");

async function transcribeAudio() {
  try {
    const formData = new FormData();
    const audioFilePath = path.join(__dirname, 'audio.opus');
    formData.append("file", fs.createReadStream(audioFilePath));

    const response = await axios.post("http://44.192.32.169:2000/transcribe/", formData, {
      headers: {
        ...formData.getHeaders(),
      },
    });

    console.log("🚀 ~ ConnectionManager ~ transcribeAudio ~ response:", response.data);
    return response.data;
  } catch (error) {
    console.log("🚀 ~ transcribeAudio ~ error:", error);
  }
}

transcribeAudio();
