//! A crash-safe on-disk block store — mirrors `netnode/store.py`. NOT money.
//!
//! Length-prefixed append (`[len:4 LE][raw]`), fsync'd; `read_all` ignores a crash-truncated tail
//! (a partial final record), so a node recovers cleanly after an ill-timed crash.

use std::fs::{File, OpenOptions};
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};

pub struct BlockStore {
    path: PathBuf,
    file: File,
}

impl BlockStore {
    pub fn open(dir: &Path) -> io::Result<Self> {
        std::fs::create_dir_all(dir)?;
        let path = dir.join("blocks.dat");
        let file = OpenOptions::new().create(true).read(true).append(true).open(&path)?;
        Ok(BlockStore { path, file })
    }

    /// Append a block and flush it to disk.
    pub fn append(&mut self, raw: &[u8]) -> io::Result<()> {
        self.file.write_all(&(raw.len() as u32).to_le_bytes())?;
        self.file.write_all(raw)?;
        self.file.sync_all()?;
        Ok(())
    }

    /// All whole records, ignoring a crash-truncated final one.
    pub fn read_all(&self) -> io::Result<Vec<Vec<u8>>> {
        let mut data = Vec::new();
        File::open(&self.path)?.read_to_end(&mut data)?;
        let mut out = Vec::new();
        let mut i = 0;
        while i + 4 <= data.len() {
            let n = u32::from_le_bytes(data[i..i + 4].try_into().unwrap()) as usize;
            i += 4;
            if i + n > data.len() {
                break; // truncated tail -> ignore
            }
            out.push(data[i..i + n].to_vec());
            i += n;
        }
        Ok(out)
    }
}
