from pydantic import BaseModel, ConfigDict, Field
import numpy as np
from sklearn.neighbors import NearestNeighbors


class RelatedTopicsNearestNeighbors(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_to_idx: dict[str, int] = Field(..., description="The node to index mapping")
    nodes: list[str] = Field(..., description="The nodes")
    X: np.ndarray = Field(..., description="The embeddings")
    X_cos: np.ndarray = Field(..., description="The normalized embeddings")
    nn: NearestNeighbors = Field(..., description="The nearest neighbors")
