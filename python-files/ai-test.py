class MyClass(GeneratedClass):
    """Box de teste para simular entrada de texto transcrito."""

    MOCK_TEXT = (
        "Olá NAO, como vai? Isso é um teste de áudio e conexão de JBL no seu sistema. "
        "Fale algumas frases para testarmos o áudio como aqueles interlocutores de rádio "
        "ou um check-list de testes."
    )

    def __init__(self):
        GeneratedClass.__init__(self)

    def onLoad(self):
        pass

    def onUnload(self):
        pass

    def onInput_onStart(self):
        self.transcriptedText(self.MOCK_TEXT)
        self.onStopped()