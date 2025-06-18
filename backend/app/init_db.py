import asyncio
from database import engine
from models.audio_files import Base as AudioBase
from models.transcripts import Base as TranscriptBase
from models.transcription_chunks import Base as ChunkBase
from models.verbs import Base as Verbs
from models.prompts import Base as Prompt

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(AudioBase.metadata.create_all)
        await conn.run_sync(TranscriptBase.metadata.create_all) 
        await conn.run_sync(ChunkBase.metadata.create_all)
        await conn.run_sync(Verbs.metadata.create_all)
        await conn.run_sync(Prompt.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(init_db())
