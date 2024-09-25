#!/usr/bin/env python
from vtkmodules.vtkCommonExecutionModel import vtkStreamingDemandDrivenPipeline
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkIOEnSight import vtkGenericEnSightReader
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkHierarchicalPolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer,
)
import vtkmodules.vtkInteractionStyle
import vtkmodules.vtkRenderingFreeType
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.util.misc import vtkGetDataRoot
VTK_DATA_ROOT = vtkGetDataRoot()

# create a rendering window and renderer
ren1 = vtkRenderer()
renWin = vtkRenderWindow()
renWin.AddRenderer(ren1)
renWin.StereoCapableWindowOn()
iren = vtkRenderWindowInteractor()
iren.SetRenderWindow(renWin)
reader = vtkGenericEnSightReader()
reader.SetCaseFileName(VTK_DATA_ROOT + "/Data/EnSight/elements6-bin.case")
reader.UpdateInformation()
reader.GetOutputInformation(0).Set(vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), 0.1)
geom = vtkGeometryFilter()
geom.SetInputConnection(reader.GetOutputPort())
mapper = vtkHierarchicalPolyDataMapper()
mapper.SetInputConnection(geom.GetOutputPort())
mapper.SetColorModeToMapScalars()
mapper.SetScalarModeToUsePointFieldData()
mapper.ColorByArrayComponent("pointTensors",0)
mapper.SetScalarRange(0,300)
actor = vtkActor()
actor.SetMapper(mapper)
# assign our actor to the renderer
ren1.AddActor(actor)
# enable user interface interactor
iren.Initialize()
renWin.Render()
# prevent the tk window from showing up then start the event loop
reader.SetDefaultExecutivePrototype(None)
# --- end of script --
