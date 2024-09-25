// SPDX-FileCopyrightText: Copyright (c) Ken Martin, Will Schroeder, Bill Lorensen
// SPDX-License-Identifier: BSD-3-Clause
/**
 * @class   vtkTransmitRectilinearGridPiece
 * @brief   Redistributes data produced
 * by serial readers
 *
 *
 * This filter can be used to redistribute data from producers that can't
 * produce data in parallel. All data is produced on first process and
 * the distributed to others using the multiprocess controller.
 */

#ifndef vtkTransmitStructuredDataPiece_h
#define vtkTransmitStructuredDataPiece_h

#include "vtkDataSetAlgorithm.h"
#include "vtkFiltersParallelModule.h" // For export macro

VTK_ABI_NAMESPACE_BEGIN
class vtkMultiProcessController;

class VTKFILTERSPARALLEL_EXPORT vtkTransmitStructuredDataPiece : public vtkDataSetAlgorithm
{
public:
  static vtkTransmitStructuredDataPiece* New();
  vtkTypeMacro(vtkTransmitStructuredDataPiece, vtkDataSetAlgorithm);
  void PrintSelf(ostream& os, vtkIndent indent) override;

  ///@{
  /**
   * By default this filter uses the global controller,
   * but this method can be used to set another instead.
   */
  virtual void SetController(vtkMultiProcessController*);
  vtkGetObjectMacro(Controller, vtkMultiProcessController);
  ///@}

  ///@{
  /**
   * Turn on/off creating ghost cells (on by default).
   */
  vtkSetMacro(CreateGhostCells, vtkTypeBool);
  vtkGetMacro(CreateGhostCells, vtkTypeBool);
  vtkBooleanMacro(CreateGhostCells, vtkTypeBool);
  ///@}

protected:
  vtkTransmitStructuredDataPiece();
  ~vtkTransmitStructuredDataPiece() override;

  // Data generation method
  int RequestData(vtkInformation*, vtkInformationVector**, vtkInformationVector*) override;
  void RootExecute(vtkDataSet* input, vtkDataSet* output, vtkInformation* outInfo);
  void SatelliteExecute(int procId, vtkDataSet* output, vtkInformation* outInfo);
  int RequestInformation(vtkInformation*, vtkInformationVector**, vtkInformationVector*) override;
  int RequestUpdateExtent(vtkInformation*, vtkInformationVector**, vtkInformationVector*) override;

  vtkTypeBool CreateGhostCells;
  vtkMultiProcessController* Controller;

private:
  vtkTransmitStructuredDataPiece(const vtkTransmitStructuredDataPiece&) = delete;
  void operator=(const vtkTransmitStructuredDataPiece&) = delete;
};

VTK_ABI_NAMESPACE_END
#endif
