async function enviarMensagem()
{
    let input = document.getElementById("mensagem");

    if(!input)
    {
        console.log("Input não encontrado");
        return;
    }

    let msg = input.value;

    if(!msg)
    {
        return;
    }

    adicionarMensagem("Você: " + msg);

    try
    {
        let resposta = await fetch("/chat",
        {
            method: "POST",

            headers:
            {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(
            {
                mensagem: msg
            })
        });

        let dados = await resposta.json();

        adicionarMensagem("IA: " + dados.resposta);
    }
    catch(erro)
    {
        console.log(erro);
        adicionarMensagem("Erro ao conectar com servidor");
    }

    input.value = "";
}


function adicionarMensagem(msg)
{
    let chat = document.getElementById("chat");

    if(!chat)
    {
        console.log("Chat não encontrado");
        return;
    }

    let div = document.createElement("div");

    div.innerText = msg;

    chat.appendChild(div);

    chat.scrollTop = chat.scrollHeight;
}