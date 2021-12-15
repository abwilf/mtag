import torch
from tqdm import tqdm
import numpy as np
from torch_geometric.nn import Linear

from hetero_conv import HeteroConv
from torch_geometric.nn import GCNConv, SAGEConv, GATConv, GATv2Conv, Linear
from torch_scatter import scatter_mean
import torch.nn.functional as F
from gatv3conv import GATv3Conv
from torch_geometric.data import HeteroData
from torch_geometric.data import Data
from HeteroDataLoader import DataLoader
import torch_geometric.transforms as T

import torch
import torch.nn as nn
import torch.optim as optim
from collections import OrderedDict

from .mylstm import MyLSTM
from .social_iq import *
from .alex_utils import *
from .graph_builder import *
from .global_const import gc

# get all connection types for declaring heteroconv later
mods = ['text', 'audio', 'video']
conn_types = ['past', 'pres', 'fut']
all_connections = []
for mod in mods:
    for mod2 in mods:
        for conn_type in conn_types:
            all_connections.append((mod, conn_type, mod2))

NUM_QS = 6
NUM_A_COMBS = 12

def get_fc_edges(edges_a, edges_b):
    return torch.cat([elt[None,:] for elt in torch.meshgrid(edges_a, edges_b)]).reshape(2,-1)


def get_masked(arr):
    if (arr==0).all():
        return torch.tensor([]).to(torch.float32)
    else:
        if 'mosi' in gc['dataset'] or 'iemocap' in gc['dataset']: # front padded
            idx = (arr==0).all(dim=-1).to(torch.long).argmin()
            return arr[idx:]

        elif 'social' in gc['dataset']: # back padded
            # find idx of last zero element looking from back to front
            idx = (arr==0).all(dim=-1).to(torch.long).flip(dims=[0]).argmin()
            return arr[:-idx]
            
        else: 
            assert False, 'Only social, mosi, and iemocap are supported right now.  To add another dataset, break here and see whether front or back padded to seq len'
    

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term[:d_model // 2])  # Added to support odd d_model
        pe = pe.unsqueeze(0).transpose(0, 1).squeeze()
        self.register_buffer('pe', pe)

    def forward(self, x, counts):
        pe_rel = torch.cat([self.pe[:count,:] for count in counts])
        x = x + pe_rel.to(gc['device'])
        return self.dropout(x)
